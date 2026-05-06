# -*- coding: utf-8 -*-

import re
import os
import logging
import ipaddress
import urllib.parse
import sys
import json
from collections import OrderedDict, deque
from collections.abc import Callable
from typing import Any

# 定义安全扫描引擎支持的所有高危操作与恶意规则的唯一标识符（ID）列表。
RULE_ROW_IDS: tuple[str, ...] = (
    "pm_custom_source", "upload_like_exfil", "icmp_payload_exfil", "stealth_background", "redirect_sensitive_or_persistence",
    "process_sub_network_exec", "source_process_sub_network", "shellc_command_sub_network", "eval_source_command_sub_network",
    "staged_download_execute", "herestring_network_exec", "netcat_exec", "destructive_tool_family", "suid_bit_set",
    "wrapper_dynamic_shell", "tee_sensitive_or_persistence", "pipe_network_to_shell", "decode_to_shell", "dd_raw_disk",
    "rm_rf_core", "tar_checkpoint_exec", "shellc_inline_netpipe", "python_network_run", "python_dynamic_exec", "node_dynamic_exec",
    "powershell_dynamic_exec_surface", "interpreter_input_exec", "dynamic_eval", "generic_process_sub_exec", "dynamic_shell_payload",
    "xargs_shell", "awk_system_dynamic", "broad_permission_change", "recursive_ownership_change", "pwsh_iex_download_exec",
    "pwsh_execution_policy", "pwsh_outfile_download", "win_run_key_persistence", "win_userinit_tamper", "win_schtasks_persist",
    "win_service_persist", "win_admin_grant", "win_destructive_delete", "win_firewall_disable", "win_defender_policy_tamper",
    "win_backup_destroy", "win_bcdedit_tamper", "win_certutil_bitsadmin_download", "win_disk_destructive_ops",
)


# 规则元数据字典：将上述规则 ID 映射到具体的内部检测状态码 ID 以及对应的校验函数名。
RULE_ROW_META: dict[str, dict[str, Any]] = {
    "pm_custom_source": {"rule_ids": ("BLOCK_PM_CUSTOM_SOURCE_MALICIOUS", "REVIEW_PM_CUSTOM_SOURCE"), "function": "_check_ecosystem_trust"},
    "upload_like_exfil": {"rule_ids": ("BLOCK_EXFIL_SENSITIVE", "REVIEW_EXFIL_SUSPECTED"), "function": "_check_data_exfiltration"},
    "icmp_payload_exfil": {"rule_ids": ("BLOCK_EXFIL_ICMP",), "function": "_check_data_exfiltration"},
    "stealth_background": {"rule_ids": ("REVIEW_BACKGROUND_DEV", "BLOCK_STEALTH_BACKGROUND"), "function": "_check_stealth_background"},
    "redirect_sensitive_or_persistence": {
        "rule_ids": ("BLOCK_REDIRECT_SENSITIVE", "REVIEW_REDIRECT_PERSISTENCE", "BLOCK_WIN_REDIRECT_SENSITIVE"),
        "function": "_check_sensitive_redirect_text",
    },
    "process_sub_network_exec": {"rule_ids": ("REVIEW_PROCESS_SUB_NET_SHELL", "BLOCK_PROCESS_SUB_MALICIOUS"), "function": "_check_bash_exec_chain_text"},
    "source_process_sub_network": {"rule_ids": ("REVIEW_SOURCE_PROCESS_SUB_NET", "BLOCK_SOURCE_PROCESS_SUB_MALICIOUS"), "function": "_check_bash_exec_chain_text"},
    "shellc_command_sub_network": {"rule_ids": ("REVIEW_SHELLC_SUB_NET_SHELL", "BLOCK_SHELLC_SUB_MALICIOUS"), "function": "_check_bash_exec_chain_text"},
    "eval_source_command_sub_network": {"rule_ids": ("REVIEW_EVAL_SUB_NET_SHELL", "BLOCK_EVAL_SUB_MALICIOUS"), "function": "_check_bash_exec_chain_text"},
    "staged_download_execute": {"rule_ids": ("REVIEW_STAGED_NET_EXEC", "BLOCK_STAGED_MALICIOUS"), "function": "_check_bash_exec_chain_text"},
    "herestring_network_exec": {"rule_ids": ("REVIEW_HERESTR_NET_SHELL", "BLOCK_HERESTR_MALICIOUS"), "function": "_check_bash_exec_chain_text"},
    "netcat_exec": {"rule_ids": ("BLOCK_NETCAT_EXEC",), "function": "_check_bash_command_node"},
    "destructive_tool_family": {"rule_ids": ("BLOCK_BANNED_TOOL",), "function": "_check_bash_command_node"},
    "suid_bit_set": {"rule_ids": ("BLOCK_SUID",), "function": "_check_bash_command_node"},
    "wrapper_dynamic_shell": {"rule_ids": ("REVIEW_WRAPPER_DYNAMIC",), "function": "_check_bash_command_node"},
    "tee_sensitive_or_persistence": {"rule_ids": ("BLOCK_TEE_SENSITIVE", "REVIEW_TEE_PERSISTENCE"), "function": "_check_bash_command_node"},
    "pipe_network_to_shell": {"rule_ids": ("BLOCK_PIPE_MALICIOUS", "REVIEW_PIPE_NET_SHELL"), "function": "_check_bash_pipeline"},
    "decode_to_shell": {"rule_ids": ("BLOCK_PIPE_DECODE_NET_SHELL", "REVIEW_PIPE_DECODE_SHELL"), "function": "_check_bash_pipeline"},
    "dd_raw_disk": {"rule_ids": ("BLOCK_DD_RAW_DISK",), "function": "_analyze_bash_command"},
    "rm_rf_core": {"rule_ids": ("BLOCK_RM_RF_CORE",), "function": "_analyze_bash_command"},
    "tar_checkpoint_exec": {"rule_ids": ("BLOCK_TAR_EXEC",), "function": "_analyze_bash_command"},
    "shellc_inline_netpipe": {"rule_ids": ("BLOCK_SHELLC_NETPIPE", "REVIEW_SHELLC_NETPIPE"), "function": "_analyze_bash_command"},
    "python_network_run": {"rule_ids": ("BLOCK_PY_NET_MALICIOUS", "REVIEW_PY_NETPIPE"), "function": "_analyze_bash_command"},
    "python_dynamic_exec": {"rule_ids": ("REVIEW_PY_DYNAMIC_EXEC",), "function": "_analyze_bash_command"},
    "node_dynamic_exec": {"rule_ids": ("REVIEW_NODE_DYNAMIC_EXEC",), "function": "_analyze_bash_command"},
    "powershell_dynamic_exec_surface": {"rule_ids": ("REVIEW_PWSH_DYNAMIC_EXEC",), "function": "_analyze_bash_command"},
    "interpreter_input_exec": {"rule_ids": ("REVIEW_INTERPRETER_INPUT_EXEC",), "function": "_analyze_bash_command"},
    "dynamic_eval": {"rule_ids": ("REVIEW_DYNAMIC_EVAL",), "function": "_analyze_bash_command"},
    "generic_process_sub_exec": {"rule_ids": ("REVIEW_PROCESS_SUB_EXEC",), "function": "_analyze_bash_command"},
    "dynamic_shell_payload": {"rule_ids": ("REVIEW_DYNAMIC_SHELL_PAYLOAD",), "function": "_analyze_bash_command"},
    "xargs_shell": {"rule_ids": ("REVIEW_XARGS_SHELL",), "function": "_analyze_bash_command"},
    "awk_system_dynamic": {"rule_ids": ("REVIEW_AWK_SYSTEM",), "function": "_analyze_bash_command"},
    "broad_permission_change": {"rule_ids": ("BLOCK_CORE_PERMISSION_OPEN", "REVIEW_BROAD_PERMISSION"), "function": "_check_broad_permission_context"},
    "recursive_ownership_change": {"rule_ids": ("BLOCK_OWNERSHIP_CORE", "REVIEW_OWNERSHIP_RECURSIVE"), "function": "_analyze_bash_command"},
    "pwsh_iex_download_exec": {"rule_ids": ("BLOCK_PWSH_MALICIOUS_NET", "REVIEW_PWSH_NET_EXEC"), "function": "_check_windows_specific_risks"},
    "pwsh_execution_policy": {"rule_ids": ("REVIEW_PWSH_EXEC_POLICY",), "function": "_check_windows_specific_risks"},
    "pwsh_outfile_download": {"rule_ids": ("BLOCK_PWSH_DOWNLOAD_MALICIOUS", "REVIEW_PWSH_DOWNLOAD"), "function": "_check_windows_specific_risks"},
    "win_run_key_persistence": {"rule_ids": ("BLOCK_WIN_REG_AUTOSTART",), "function": "_check_windows_specific_risks"},
    "win_userinit_tamper": {"rule_ids": ("BLOCK_WIN_BOOT_TAMPER",), "function": "_check_windows_specific_risks"},
    "win_schtasks_persist": {"rule_ids": ("BLOCK_WIN_SCHTASK_PERSIST",), "function": "_check_windows_specific_risks"},
    "win_service_persist": {"rule_ids": ("BLOCK_WIN_SERVICE_PERSIST",), "function": "_check_windows_specific_risks"},
    "win_admin_grant": {"rule_ids": ("BLOCK_WIN_PRIV_GRANT",), "function": "_check_windows_specific_risks"},
    "win_destructive_delete": {"rule_ids": ("BLOCK_WIN_DESTRUCTIVE_DELETE",), "function": "_check_windows_specific_risks"},
    "win_firewall_disable": {"rule_ids": ("BLOCK_WIN_DISABLE_FIREWALL",), "function": "_check_windows_specific_risks"},
    "win_defender_policy_tamper": {"rule_ids": ("REVIEW_WIN_SECURITY_POLICY",), "function": "_check_windows_specific_risks"},
    "win_backup_destroy": {"rule_ids": ("BLOCK_WIN_BACKUP_DESTROY",), "function": "_check_windows_specific_risks"},
    "win_bcdedit_tamper": {"rule_ids": ("BLOCK_WIN_BOOT_TAMPER",), "function": "_check_windows_specific_risks"},
    "win_certutil_bitsadmin_download": {
        "rule_ids": ("BLOCK_WIN_DL_EXEC", "REVIEW_WIN_DL_EXEC", "BLOCK_WIN_DOWNLOAD_MALICIOUS", "REVIEW_WIN_DOWNLOAD"),
        "function": "_check_windows_specific_risks",
    },
    "win_disk_destructive_ops": {"rule_ids": ("BLOCK_WIN_DESTRUCTIVE", "BLOCK_WIN_DISKPART_CLEAN"), "function": "_check_windows_specific_risks"},
}

# 规则测试或展示用的示例危险命令（仅作元数据展示使用）。
_RULE_COMMAND_OVERRIDES: dict[str, str] = {
    "staged_download_execute": "curl ... > file && bash file",
    "win_userinit_tamper": "reg add HKLM...Winlogon Userinit",
    "win_bcdedit_tamper": "bcdedit ...",
    "win_certutil_bitsadmin_download": "certutil|bitsadmin + http",
}

# 规则豁免条件的文字描述说明（仅作元数据展示使用）。
_RULE_EXCLUDED_CASE_OVERRIDES: dict[str, str] = {
    "staged_download_execute": "只下载不执行。",
}

# 整合并生成给外部调用的规则配置全集列表。
SCANNER_MALICIOUS_RULE_ROWS: list[dict[str, Any]] = [
    {
        "row_id": row_id,
        "rule_ids": tuple(RULE_ROW_META.get(row_id, {}).get("rule_ids", ("UNKNOWN_RULE_ID",))),
        "malicious_command": _RULE_COMMAND_OVERRIDES.get(row_id, row_id),
        "excluded_cases": _RULE_EXCLUDED_CASE_OVERRIDES.get(row_id, "见规则函数中的排除条件。"),
        "purpose": "用于识别潜在高风险命令模式。",
        "function": str(RULE_ROW_META.get(row_id, {}).get("function", "_check_unknown_rule")),
    }
    for row_id in RULE_ROW_IDS
]

try:
    from tree_sitter import Language, Parser
    import tree_sitter_bash
    HAS_TREE_SITTER_BASH = True
except ImportError:
    HAS_TREE_SITTER_BASH = False

# 限制单次检测的最大命令长度为 512KB，防止消耗过多资源（ReDoS或内存耗尽）。
MAX_COMMAND_BYTES = 512 * 1024

# 预定义的官方受信任域名，用于过滤包管理器下载或安装脚本的误报。
TRUSTED_INSTALL_DOMAINS = {
    "raw.githubusercontent.com",
    "sh.rustup.rs",
    "bun.sh",
    "deno.land",
    "get.docker.com",
    "deb.nodesource.com",
    "install.python-poetry.org",
    "golang.org",
    "pypi.org",
    "files.pythonhosted.org",
    "registry.npmjs.org",
    "registry.yarnpkg.com",
    "crates.io",
    "static.crates.io",
    "proxy.golang.org",
    "sum.golang.org",
    "deb.debian.org",
    "security.ubuntu.com",
    "archive.ubuntu.com",
    "formulae.brew.sh",
}

# 代理环境与信任等级常量配置。
DEFAULT_AGENT_ENV = "persistent_host"
EPHEMERAL_AGENT_ENV = "ephemeral_sandbox" # 短暂存活的沙箱环境（可放宽破坏性操作的拦截等级）
DEFAULT_TRUST_PROFILE = "developer"
TRUST_PROFILES = {"strict", "developer", "enterprise"}
# 如果当前环境是沙箱（ephemeral_sandbox），这几个硬性拦截操作将被降级为仅需“复核（Review）”
SANDBOX_DOWNGRADE_RULES = {
    "BLOCK_DD_RAW_DISK",
    "BLOCK_RM_RF_CORE",
    "BLOCK_CORE_PERMISSION_OPEN",
    "BLOCK_OWNERSHIP_CORE",
}

# --- 用于正则扫描的预编译 Pattern ---
# 包管理工具特征
PACKAGE_MANAGER_ALLOW_RE = re.compile(
    r"^\s*(?:python\s+-m\s+pip|pip(?:3)?|npm|yarn|pnpm|cargo|go|get|apt(?:-get)?|brew)\b",
    re.IGNORECASE,
)
# 包管理工具使用非官方/自定义源的特征
PACKAGE_MANAGER_CUSTOM_SOURCE_RE = re.compile(
    r"(?:--index-url|--extra-index-url|--registry|--source|\s-i\s+|GOPROXY=|PIP_INDEX_URL=|NPM_CONFIG_REGISTRY=)",
    re.IGNORECASE,
)
# 常见的网络外连传输工具
NETWORK_EGRESS_RE = re.compile(
    r"\b(?:curl|wget|invoke-webrequest|iwr|invoke-restmethod|irm|httpie|http|scp|rsync|ftp|tftp|nc|netcat|ping)\b",
    re.IGNORECASE,
)
# 网络工具附带本地数据向外发送（外泄）的特征参数
EgressUploadHint_RE = re.compile(
    r"(?:\b(?:-x\s+post|post|put|patch)\b|\b--data(?:-binary|-raw|-urlencode)?\b|\b-f\b|\b--form\b|@[\w./\\%-]+|\bping\b[^\n;|&]*\s-p\s+[0-9a-f]+)",
    re.IGNORECASE,
)
# 敏感文件（如密钥、环境配置）的后缀或名称特征
SENSITIVE_REF_RE = re.compile(
    r"(?:^|[\\/])(?:\.env(?:\.[^\\/]+)?|id_rsa|id_ed25519|authorized_keys|known_hosts|credentials|"
    r"config(?:\.json)?|secrets?\.ya?ml|.*\.(?:pem|p12|pfx|key))(?:$|[\s\"'])",
    re.IGNORECASE,
)
# 隐蔽在后台常驻运行的工具特征
STEALTH_BACKGROUND_RE = re.compile(
    r"(?:\bnohup\b.*&\s*$|&\s*$|\bdisown\b|\bsetsid\b|\btmux\b[^\n;|&]*(?:new|new-session)\b|\bscreen\b[^\n;|&]*\b-dm\b)",
    re.IGNORECASE,
)
# 开发者常规的本地 Web 服务特征（用于豁免后台运行告警）
SAFE_DEV_BACKGROUND_RE = re.compile(
    r"\b(?:python\s+-m\s+http\.server|npm\s+run\s+dev|vite|next\s+dev|uvicorn|flask\s+run)\b",
    re.IGNORECASE,
)

# 历史会话上下文存储配置，用于跨命令行为关联追踪。
SESSION_EVENT_LIMIT = 64
SESSION_LIMIT = 1024
TAINTED_FILE_SUFFIXES = (".sh", ".bash", ".zsh", ".py", ".ps1", ".bat", ".cmd", ".exe", ".dll")
WORKSPACE_SAFE_PREFIXES = ("/tmp", "/var/tmp", "/private/tmp", "%temp%", "$env:temp")
RAW_GITHUB_HOST = "raw.githubusercontent.com"
DEV_RAW_GITHUB_INSTALLER_PREFIXES = (
    "/homebrew/install/",
    "/nvm-sh/nvm/",
    "/pyenv/pyenv-installer/",
    "/astral-sh/uv/",
    "/ohmyzsh/ohmyzsh/",
)
DEV_LOG_FILE_HINT_RE = re.compile(
    r"(?:^|[._-])(?:log|logs|trace|traces|crash|debug|stderr|stdout|report)(?:[._-]|$)",
    re.IGNORECASE,
)

# Linux 危险破坏性命令（物理格式化或粉碎文件）
BANNED_EXACT = {"wipefs", "shred"}
BANNED_PREFIX = ("mkfs",)

# Linux 磁盘底层设备路径匹配
RAW_DISK_PATH = (
    r"/dev/(?:sd[a-z]\d*|vd[a-z]\d*|xvd[a-z]\d*|"
    r"nvme\d+n\d+(?:p\d+)?|mmcblk\d+(?:p\d+)?)"
)

# Windows 核心系统路径与注册表
WINDOWS_SENSITIVE_PATHS = (
    r"C:[\\/]Windows[\\/]System32|"
    r"C:[\\/]Windows[\\/]System32[\\/]drivers[\\/]etc[\\/]hosts|"
    r"C:[\\/]Users[\\/][^\\]+[\\/]ntuser\.dat|"
    r"/mnt/c/Windows/System32"
)

# 严禁直接写入或重定向覆盖的系统级敏感文件
BLOCK_WRITE_PATHS = re.compile(
    r"^(?:"
    r"/etc/shadow|/etc/passwd|/etc/sudoers|/etc/cron(?:\.d)?|"
    r"/root/\.ssh(?:/authorized_keys)?|~/.bash_history|"
    + WINDOWS_SENSITIVE_PATHS +
    r")(?=$|/|[\s\"'])",
    re.IGNORECASE,
)

# 探测是否为 Bash 命令的特征关键词
BASH_HINT_RE = re.compile(
    r"(?:\b(?:bash|sh|zsh|curl|wget|fetch|dd|chmod|chown|tee|source|eval|"
    r"nc|netcat|mkfs|wipefs|shred|tar|awk|xargs|rm|python|git|ssh|find|grep|"
    r"cat|tail|head)\b|/etc/|/dev/|<\(|\$\()",
    re.IGNORECASE,
)

# 探测是否为 Windows / PowerShell 命令的特征关键词
WINDOWS_HINT_RE = re.compile(
    r"(?:\b(?:powershell|pwsh|invoke-webrequest|iwr|invoke-expression|iex|"
    r"set-executionpolicy|reg\s+(?:add|delete)|schtasks|vssadmin|format(?:-volume)?|"
    r"diskpart|bcdedit|certutil|bitsadmin|wbadmin|netsh|sc\s+create)\b|"
    r"[a-z]:[\\/]|%[a-z_]+%)",
    re.IGNORECASE,
)

# dd 命令强行覆写磁盘底层设备的特征
DD_RAW_DISK_RE = re.compile(
    rf"\bdd\b[^\n;|&]*\bof\s*=\s*[\"']?{RAW_DISK_PATH}(?=$|[\"'\s])",
    re.IGNORECASE,
)

# 匹配重定向符号（>>, >|）后的输出目标文件
REDIRECT_TARGET_RE = re.compile(r"(?:>>?|>\|)\s*(\"[^\"]+\"|'[^']+'|[^\s;|&]+)")
NETWORK_TOOL_PATTERN = r"(?:curl|wget|fetch)"
SHELL_PATTERN = r"(?:sh|bash|zsh)"
# 匹配下载命令中的目标本地保存路径（-o / --output）
DOWNLOAD_PATH_RE = re.compile(
    r"(?:\b(?:curl|wget)\b[^\n;|&]*(?:-o|--output)\s+|(?:-outfile)\s+)(\"[^\"]+\"|'[^']+'|[^\s;|&]+)",
    re.IGNORECASE,
)

# 常见用于实现后门驻留（持久化）的文件写入路径（仅作复核告警）
REVIEW_WRITE_PATHS = re.compile(
    r"^(?:"
    r"~/(?:\.bashrc|\.zshrc|\.profile|\.ssh/config)|"
    r"/etc/(?:profile|bash\.bashrc|systemd/system)|"
    r"/etc/ld\.so\.preload|/etc/rc\.local|"
    r"/usr/lib/systemd/system|"
    r"~/.config/(?:systemd/user|autostart)|"
    r"~/Library/LaunchAgents|/Library/LaunchDaemons|"
    r"C:[\\/](?:ProgramData[\\/]Microsoft[\\/]Windows[\\/]Start Menu[\\/]Programs[\\/]Startup)"
    r")(?=$|/|[\s\"'])",
    re.IGNORECASE,
)

# 解释器直接执行外部文件的特征（如 `bash script.sh`）
INTERPRETER_EXEC_PATH_RE = re.compile(
    r"\b(?:bash|sh|zsh|python(?:3)?|node|pwsh|powershell)\b\s+(\"[^\"]+\"|'[^']+'|[^\s;|&]+)",
    re.IGNORECASE,
)
# `source` 或 `.` 引用执行脚本特征
SOURCE_PATH_RE = re.compile(r"\b(?:source|\.)\b\s+(\"[^\"]+\"|'[^']+'|[^\s;|&]+)", re.IGNORECASE)
# 直接调用可执行脚本或二进制的特征（如 `./script.sh`）
DIRECT_SCRIPT_EXEC_RE = re.compile(
    r"(?:^|[;&]\s*)(?:\./[^\s;|&]+|[^\s;|&]+\.(?:sh|bash|zsh|py|ps1|bat|cmd|exe))(?=$|[\s;|&])",
    re.IGNORECASE,
)
# 归档解压命令特征
ARCHIVE_EXTRACT_RE = re.compile(r"\b(?:tar|unzip)\b[^\n;|&]*(?:\b-x|\b-xf|\bextract\b)", re.IGNORECASE)
# Base64 等编码解码执行的特征（用于规避静态检测）
DECODE_HINT_RE = re.compile(
    r"\b(?:base64|openssl|xxd|certutil)\b[^\n;|&]*(?:-d|--decode|-decode|-r)|"
    r"(?:frombase64string|buffer\.from\s*\([^)]*base64)",
    re.IGNORECASE,
)

# 恶意远程主机的常见关键字特征
MALICIOUS_HOST_HINT_RE = re.compile(
    r"(?:^|[.-])(mal|malicious|attacker|evil|payload|c2)(?:[.-]|$)",
    re.IGNORECASE,
)

# 结合重定向、管道、命令替换的网络注入执行链（如 shell 从网络直读执行）的正则配置
BASH_EXEC_CHAIN_TEXT_RULES = (
    (
        rf"\b{SHELL_PATTERN}\b[^\n;|&]*<\(\s*{NETWORK_TOOL_PATTERN}\b",
        "REVIEW_PROCESS_SUB_NET_SHELL",
        "BLOCK_PROCESS_SUB_MALICIOUS",
        "process substitution download and execute",
    ),
    (
        rf"\b(?:source|\.)\b[^\n;|&]*<\(\s*{NETWORK_TOOL_PATTERN}\b",
        "REVIEW_SOURCE_PROCESS_SUB_NET",
        "BLOCK_SOURCE_PROCESS_SUB_MALICIOUS",
        "source process substitution from network",
    ),
    (
        rf"\b{SHELL_PATTERN}\b[^\n;|&]*\s-c\b[^\n;|&]*\$\([^\)]*\b{NETWORK_TOOL_PATTERN}\b",
        "REVIEW_SHELLC_SUB_NET_SHELL",
        "BLOCK_SHELLC_SUB_MALICIOUS",
        "shell -c command substitution from network",
    ),
    (
        rf"\b(?:eval|source|\.)\b[^\n;|&]*\$\([^\)]*\b{NETWORK_TOOL_PATTERN}\b",
        "REVIEW_EVAL_SUB_NET_SHELL",
        "BLOCK_EVAL_SUB_MALICIOUS",
        "eval/source command substitution from network",
    ),
    (
        rf"\b{NETWORK_TOOL_PATTERN}\b[^\n;|&]*>\s*[^\s;|&]+[^\n;|&]*&&[^\n;|&]*\b{SHELL_PATTERN}\b",
        "REVIEW_STAGED_NET_EXEC",
        "BLOCK_STAGED_MALICIOUS",
        "staged download and execute",
    ),
    (
        rf"\b{NETWORK_TOOL_PATTERN}\b[^\n;|&]*(?:-o|--output)\s+[^\s;|&]+[^\n;|&]*&&[^\n;|&]*\b{SHELL_PATTERN}\b",
        "REVIEW_STAGED_NET_EXEC",
        "BLOCK_STAGED_MALICIOUS",
        "staged download and execute",
    ),
    (
        rf"\b{SHELL_PATTERN}\b[^\n;|&]*<<<[^\n;|&]*\$\([^\)]*\b{NETWORK_TOOL_PATTERN}\b",
        "REVIEW_HERESTR_NET_SHELL",
        "BLOCK_HERESTR_MALICIOUS",
        "here-string network execution",
    ),
)

EngineResult = dict[str, Any]
PublicResult = dict[str, Any]
RuleChecker = Callable[[str, dict[str, Any]], EngineResult | None]
LOGGER = logging.getLogger(__name__)


def _sanitize_rule_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """ 对传入的规则元数据进行格式清洗和默认值补全，确保其可被引擎安全调用。
    Args:
        rows (list[dict[str, Any]]): 原始的规则字典列表。
    Returns:
        list[dict[str, Any]]: 格式化后的标准规则列表。
    """
    sanitized: list[dict[str, Any]] = []
    for item in rows:
        row_id = str(item.get("row_id", "unknown_rule")).strip() or "unknown_rule"
        function = str(item.get("function", "unknown")).strip() or "unknown"
        rule_ids = tuple(str(rule_id) for rule_id in item.get("rule_ids", ()) if str(rule_id).strip())
        if not rule_ids:
            rule_ids = ("UNKNOWN_RULE_ID",)
        sanitized.append(
            {
                "row_id": row_id,
                "rule_ids": rule_ids,
                "malicious_command": str(item.get("malicious_command", row_id)),
                "excluded_cases": str(item.get("excluded_cases", "见规则函数中的排除条件。")),
                "purpose": str(item.get("purpose", "用于识别潜在高风险命令模式。")),
                "function": function,
            }
        )
    return sanitized


SCANNER_MALICIOUS_RULE_ROWS = _sanitize_rule_rows(SCANNER_MALICIOUS_RULE_ROWS)


def list_scanner_malicious_regex_rules() -> list[dict[str, Any]]:
    """ 返回引擎加载的所有扫描规则数据。
    Returns:
        list[dict[str, Any]]: 规则配置列表副本。
    """
    return [dict(rule) for rule in SCANNER_MALICIOUS_RULE_ROWS]

def list_bash_malicious_regex_rules() -> list[dict[str, Any]]:
    """ 兼容性接口：等同于 list_scanner_malicious_regex_rules()。
    Returns:
        list[dict[str, Any]]: 规则配置列表副本。
    """
    return list_scanner_malicious_regex_rules()


class ExecutionContextStore:
    """ 会话上下文存储器：维护历史执行记录（如下载文件的路径），用于跨命令检测“下载后立即执行”等关联性高危操作。"""
    def __init__(self, max_events: int = SESSION_EVENT_LIMIT, max_sessions: int = SESSION_LIMIT):
        """ 初始化上下文存储器。
        Args:
            max_events (int): 单个会话保存的事件最大数量。
            max_sessions (int): 引擎允许同时追踪的会话最大数量（采用 LRU 淘汰）。
        """
        self._max_events = max_events
        self._max_sessions = max_sessions
        self._events: OrderedDict[str, deque[dict[str, Any]]] = OrderedDict()

    def _touch(self, key: str) -> None:
        """ 更新会话的活跃状态（移至 OrderedDict 末尾以防被 LRU 淘汰）。
        Args:
            key (str): 会话 ID。
        """
        try:
            self._events.move_to_end(key)
        except KeyError:
            return

    def get(self, session_id: str) -> list[dict[str, Any]]:
        """ 获取指定会话的历史事件列表。
        Args:
            session_id (str): 会话 ID。
        Returns:
            list[dict[str, Any]]: 当前会话存储的事件列表副本。
        """
        key = session_id or "default"
        if key not in self._events:
            return []
        self._touch(key)
        return list(self._events[key])

    def append(self, session_id: str, events: list[dict[str, Any]]) -> None:
        """ 追加新事件记录到指定会话中。若超过限制，触发淘汰机制。
        Args:
            session_id (str): 会话 ID。
            events (list): 需要追加的事件字典列表。
        """
        if not events:
            return
        key = session_id or "default"
        queue = self._events.get(key)
        if queue is None:
            queue = deque(maxlen=self._max_events)
            self._events[key] = queue
            self._touch(key)
            while len(self._events) > self._max_sessions:
                self._events.popitem(last=False)
        else:
            self._touch(key)
        for item in events:
            queue.append(item)


EXECUTION_CONTEXT_STORE = ExecutionContextStore()


def _result(code: int, message: str, rule_id: str) -> dict[str, Any]:
    """ 构造安全扫描引擎的内部结果字典。
    Args:
        code (int): 内部状态码（0=安全，1=拦截，2=复核）。
        message (str): 扫描结果的说明信息。
        rule_id (str): 触发的检测规则 ID。
    Returns:
        dict[str, Any]: 结构化返回结果。
    """
    return {"code": code, "message": message, "rule_id": rule_id}


def _normalize_token(token: str) -> str:
    """ 去除字符串两端的引号包裹，并展开起始位置的 `$HOME` 环境变量。
    Args:
        token (str): 原始字符串片段。
    Returns:
        str: 规范化后的字符串。
    """
    value = (token or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    value = value.strip("'\"")
    value = re.sub(r"^\$HOME(?=/|$)", "~", value)
    return value.strip()


def _contains_var_or_substitution(text: str) -> bool:
    """ 检查命令行中是否含有环境变量或命令执行替换（如 `$`、`$()`、`<()`），用于判断该命令是否由动态拼接生成。
    Args:
        text (str): 命令行字符串。
    Returns:
        bool: 存在动态特征时返回 True。
    """
    text = text or ""
    return any(part in text for part in ("$", "`", "$(", "${", "<(", ">("))


def _normalize_command_for_detection(text: str) -> str:
    """ 去除命令行中常见的用于对抗扫描的混淆字符（例如 Windows cmd 的 `^` 符号或 Bash 的冗余转义）。
    Args:
        text (str): 原始命令。
    Returns:
        str: 去除混淆后的干净文本。
    """
    normalized = text or ""
    # 去除 cmd.exe 中使用的 `^` 转义混淆: c^u^r^l
    normalized = normalized.replace("^", "")
    # 去除中间拼接的引号: c''url / w'g'et
    normalized = re.sub(r"(?<=\w)['\"`]+(?=\w)", "", normalized)
    # 去除行内反斜杠截断: p\ing / c\url
    normalized = re.sub(r"(?<=\w)\\(?=\w)", "", normalized)
    return normalized


def _configured_trusted_domains() -> set[str]:
    """ 从常量以及环境变量中合并获取受信任的官方包域名列表。
    Returns:
        set[str]: 小写的受信任域名白名单集合。
    """
    domains = {d.lower() for d in TRUSTED_INSTALL_DOMAINS}
    extra = os.getenv("BASH_SCANNER_TRUSTED_INSTALL_DOMAINS", "")
    for token in extra.split(","):
        item = token.strip().lower()
        if item:
            domains.add(item)
    return domains


def _is_pinned_raw_github_url(url: str) -> bool:
    """ 检查给定的 GitHub Raw 链接是否使用了固定的 Commit Hash 作为版本控制（而非不可靠的 master/main 分支）。
    Args:
        url (str): 测试的 URL 字符串。
    Returns:
        bool: 如果路径中包含 7 到 40 位的 Hash 则返回 True。
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False

    if (parsed.hostname or "").lower() != RAW_GITHUB_HOST:
        return False
    parts = [p for p in (parsed.path or "").split("/") if p]
    if len(parts) < 4:
        return False
    commit = parts[2]
    return bool(re.fullmatch(r"[0-9a-f]{7,40}", commit))


def _is_script_like_path(path_text: str) -> bool:
    """ 根据文件后缀名判断路径是否指向常见的可执行脚本。
    Args:
        path_text (str): 文件路径。
    Returns:
        bool: 如果是脚本后缀返回 True。
    """
    lowered = _normalize_token(path_text).lower()
    return lowered.endswith(TAINTED_FILE_SUFFIXES)


def _normalize_path_for_compare(path_text: str) -> str:
    """ 将路径统一转为小写、并将反斜杠（\\）替换为正斜杠（/），以进行路径比较。
    Args:
        path_text (str): 待处理路径。
    Returns:
        str: 标准化的绝对路径格式字符串。
    """
    normalized = _normalize_token(path_text).replace("\\", "/").strip().lower()
    normalized = re.sub(r"/+", "/", normalized)
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


def _is_subpath_or_same(path_text: str, root_text: str) -> bool:
    """ 判断 path_text 是否是 root_text 目录本身或其子目录。
    Args:
        path_text (str): 目标路径。
        root_text (str): 父（根）目录。
    Returns:
        bool: 存在包含关系时返回 True。
    """
    path = _normalize_path_for_compare(path_text)
    root = _normalize_path_for_compare(root_text)
    if not path or not root:
        return False
    if path == root:
        return True
    return path.startswith(root + "/")


def _is_workspace_or_temp_path(path_text: str, context: dict[str, Any]) -> bool:
    """ 检查目标路径是否属于上下文设定的工作区目录或操作系统的临时文件目录。
    在此范围内的部分写入/权限操作通常被认为是开发测试允许的安全行为。
    Args:
        path_text (str): 目标路径。
        context (dict): 包含 `cwd` 或 `workspace_roots` 的上下文信息。
    Returns:
        bool: 如果在工作区或临时目录内返回 True。
    """
    path = _normalize_path_for_compare(path_text)
    if not path:
        return False
    # 带有变量引用的路径无法直接判定，保守返回 False
    if path.startswith("$") or path.startswith("%"):
        return False
    roots = [_normalize_path_for_compare(str(x)) for x in context.get("workspace_roots", []) if str(x).strip()]
    cwd = _normalize_path_for_compare(str(context.get("cwd", "")))
    if cwd:
        roots.append(cwd)
    if roots:
        return any(_is_subpath_or_same(path, root) for root in roots if root)
    safe_prefixes = [_normalize_path_for_compare(p) for p in WORKSPACE_SAFE_PREFIXES]
    return any(_is_subpath_or_same(path, prefix) for prefix in safe_prefixes if prefix)


def _extract_shell_paths(pattern: re.Pattern[str], text: str) -> set[str]:
    """ 传入正则表达式，从文本中提取并清理出匹配的文件路径集合。
    Args:
        pattern (re.Pattern): 用于捕获路径的正则表达式。
        text (str): 被扫描文本。
    Returns:
        set[str]: 提取出的有效路径集合。
    """
    found: set[str] = set()
    for match in pattern.finditer(text or ""):
        token = _normalize_token(match.group(1) if match.groups() else match.group(0))
        if token:
            found.add(token)
    return found


def _extract_script_write_paths(cmd_text: str) -> set[str]:
    """ 提取通过 Shell 重定向（> 或 >>）目标写入的可执行脚本路径。
    Args:
        cmd_text (str): 命令行。
    Returns:
        set[str]: 重定向指向的脚本文件路径集合。
    """
    paths: set[str] = set()
    for match in REDIRECT_TARGET_RE.finditer(cmd_text or ""):
        target = _normalize_token(match.group(1))
        if target and _is_script_like_path(target):
            paths.add(target)
    return paths


def _extract_download_paths(cmd_text: str) -> set[str]:
    """ 提取网络下载工具（curl, wget, certutil）通过参数指定的本地保存文件路径。
    Args:
        cmd_text (str): 下载命令行。
    Returns:
        set[str]: 提取到的本地下载目标路径。
    """
    paths = _extract_shell_paths(DOWNLOAD_PATH_RE, cmd_text)
    cert_match = re.search(
        r"\b(?:certutil|bitsadmin)\b[^\n;|&]*https?://[^\s\"'>|]+[^\n;|&]*\s+([^\s;|&]+)$",
        cmd_text or "",
        re.IGNORECASE,
    )
    if cert_match:
        paths.add(_normalize_token(cert_match.group(1)))
    return {p for p in paths if p}


def _extract_executed_paths(cmd_text: str) -> set[str]:
    """ 提取命令行中被显式调用（如 `bash file.sh` 或 `./file.sh`）的本地脚本路径。
    Args:
        cmd_text (str): 命令行。
    Returns:
        set[str]: 被执行脚本的文件路径集合。
    """
    paths = _extract_shell_paths(INTERPRETER_EXEC_PATH_RE, cmd_text)
    for match in DIRECT_SCRIPT_EXEC_RE.finditer(cmd_text or ""):
        token = _normalize_token(match.group(0))
        if token:
            paths.add(token)
    return {p for p in paths if _is_script_like_path(p)}


def _extract_command_context(cmd_info: dict[str, Any], cmd_text: str) -> dict[str, Any]:
    """ 从外部入参中解析出扫描引擎所需的环境信息（例如工作区目录、信任等级、是否拥有特权等）。
    Args:
        cmd_info (dict): 调用方传入的上下文参数字典。
        cmd_text (str): 执行的命令（用于辅助探测是否包含 sudo 特权）。
    Returns:
        dict[str, Any]: 标准化的内部执行上下文。
    """
    roots = cmd_info.get("workspace_roots", [])
    if isinstance(roots, str):
        roots = [roots]
    cwd = str(cmd_info.get("cwd", "") or "")
    agent_env = str(cmd_info.get("agent_env") or os.getenv("AGENT_ENV", DEFAULT_AGENT_ENV)).strip().lower()
    trust_profile = str(cmd_info.get("trust_profile") or os.getenv("BASH_SCANNER_TRUST_PROFILE", DEFAULT_TRUST_PROFILE)).strip().lower()
    if trust_profile not in TRUST_PROFILES:
        trust_profile = DEFAULT_TRUST_PROFILE
    privileged = bool(cmd_info.get("is_privileged")) or bool(
        re.search(r"\b(?:sudo|pkexec|doas)\b", cmd_text or "", re.IGNORECASE)
    )
    return {
        "cwd": cwd,
        "workspace_roots": list(roots),
        "privileged": privileged,
        "agent_env": agent_env or DEFAULT_AGENT_ENV,
        "trust_profile": trust_profile,
    }


def _is_local_or_private_host(host: str) -> bool:
    """ 判断给定的域名/IP是否为本地回环（localhost）或私有内网地址。
    Args:
        host (str): 待检查的主机名或 IP。
    Returns:
        bool: 是内网/本地地址时返回 True。
    """
    hostname = (host or "").strip().lower()
    if not hostname:
        return False
    if hostname == "localhost":
        return True
    try:
        ip_addr = ipaddress.ip_address(hostname)
        return bool(ip_addr.is_loopback or ip_addr.is_private)
    except ValueError:
        return False


def _extract_urls(text: str) -> list[str]:
    """ 提取字符串中出现的所有 HTTP/HTTPS 链接。
    Args:
        text (str): 目标文本。
    Returns:
        list[str]: 包含协议和域名的 URL 列表。
    """
    return re.findall(r"https?://[^\s\"'>|]+", text or "", flags=re.IGNORECASE)


def _is_local_network_only(text: str) -> bool:
    """ 判断给定命令文本中包含的所有 URL 是否仅指向本地回环或内网私有地址。
    Args:
        text (str): 待检查命令。
    Returns:
        bool: 如果全部 URL 都在内网或本地返回 True（如果没有 URL 则返回 False）。
    """
    urls = _extract_urls(text)
    if not urls:
        return False
    hosts = []
    for url in urls:
        try:
            parsed = urllib.parse.urlparse(url)
            hosts.append(parsed.hostname or "")
        except Exception:
            return False
    return bool(hosts) and all(_is_local_or_private_host(host) for host in hosts)


def _extract_egress_payload_refs(text: str) -> list[str]:
    """ 从上传命令（如 curl）中提取通过参数（如 `@file.txt`、`-F data`）指定上传的本地文件路径。
    Args:
        text (str): 命令文本。
    Returns:
        list[str]: 被挂载/引用的文件路径列表。
    """
    refs = re.findall(r"@([^\s\"'>|]+)", text or "", flags=re.IGNORECASE)
    file_flags = re.findall(
        r"(?:--data(?:-binary|-raw|-urlencode)?|-d|--form|-F)\s+([^\s;|&]+)",
        text or "",
        flags=re.IGNORECASE,
    )
    refs.extend(file_flags)
    return [_normalize_token(item) for item in refs if item]


def _normalize_payload_ref_path(ref: str) -> str:
    """ 移除由 curl 等工具引入的 `@` 符号前缀，还原真实文件路径。
    Args:
        ref (str): 提取出的负载参数。
    Returns:
        str: 真实本地路径。
    """
    return _normalize_token(ref).lstrip("@")


def _extract_ping_hosts(cmd_text: str) -> list[str]:
    """ 提取 ping 命令所请求的目标主机或 IP 地址（忽略其 -c、-i 等参数）。
    Args:
        cmd_text (str): 包含 ping 的命令块。
    Returns:
        list[str]: 被 ping 探测的主机地址。
    """
    hosts: list[str] = []
    option_with_value = {"-c", "-i", "-s", "-w", "-W", "-t", "-I", "-M", "-m", "-p"}
    for segment in re.split(r"[;|&]+", cmd_text or ""):
        if not re.search(r"\bping\b", segment, re.IGNORECASE):
            continue
        tokens = re.findall(r"(\"[^\"]+\"|'[^']+'|[^\s]+)", segment)
        seen_ping = False
        skip_next = False
        for raw in tokens:
            token = _normalize_token(raw)
            lower = token.lower()
            if not seen_ping:
                if lower == "ping":
                    seen_ping = True
                continue
            if skip_next:
                skip_next = False
                continue
            if lower.startswith("-"):
                if lower in option_with_value:
                    skip_next = True
                continue
            if token:
                hosts.append(token)
                break
    return hosts


def _is_log_like_payload_path(path_text: str) -> bool:
    """ 根据文件名特征判断上传的本地文件是否为日志类型（开发调试中属于低风险行为）。
    Args:
        path_text (str): 上传的文件路径。
    Returns:
        bool: 如果文件名包含 log、trace 等关键字，或后缀为 .log 返回 True。
    """
    normalized = _normalize_payload_ref_path(path_text)
    if not normalized or normalized.startswith(("http://", "https://")):
        return False
    parts = re.split(r"[\\/]", normalized)
    base = (parts[-1] if parts else normalized).lower()
    if base.endswith((".log", ".jsonl", ".trace", ".trc")):
        return True
    return bool(DEV_LOG_FILE_HINT_RE.search(base))


def _is_dev_log_upload_allowed(payload_refs: list[str], context: dict[str, Any]) -> bool:
    """ 判断当前操作是否为开发者环境下被允许的日志上传行为（必须同时满足处于开发者环境、上传日志类文件、且位于工作区目录）。
    Args:
        payload_refs (list): 上传文件的路径列表。
        context (dict): 环境上下文信息。
    Returns:
        bool: 被允许的合法上传行为返回 True。
    """
    if context.get("trust_profile") not in {"developer", "enterprise"}:
        return False
    refs = [_normalize_payload_ref_path(ref) for ref in payload_refs if _normalize_payload_ref_path(ref)]
    if not refs:
        return False
    if not all(_is_workspace_or_temp_path(ref, context) for ref in refs):
        return False
    return all(_is_log_like_payload_path(ref) for ref in refs)


def _is_known_raw_github_installer_url(url: str) -> bool:
    """ 检查下载 URL 是否属于开发环境中常见合法框架（如 Homebrew, NVM, OhMyZsh 等）的安装脚本地址。
    Args:
        url (str): 测试链接。
    Returns:
        bool: 如果属于预设定的官方知名仓库路径前缀，则返回 True。
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False
    if (parsed.hostname or "").lower() != RAW_GITHUB_HOST:
        return False
    path = (parsed.path or "").lower()
    if not any(path.startswith(prefix) for prefix in DEV_RAW_GITHUB_INSTALLER_PREFIXES):
        return False
    return path.endswith((".sh", ".bash", ".zsh")) or "/install" in path


def _is_dev_install_pipeline_allowed(cmd_text: str, context: dict[str, Any]) -> bool:
    """ 分析类似 `curl ... | bash` 这样的网络直读执行命令，判断其是否为可信的开源开发包安装流程（如安装 rust 或 nvm）。
    Args:
        cmd_text (str): 执行管道命令。
        context (dict): 上下文环境。
    Returns:
        bool: 如果所有外网链接都指向可信域名/预置合法安装路径，且位于开发者环境中，则返回 True。
    """
    if context.get("trust_profile") not in {"developer", "enterprise"}:
        return False
    if not re.search(rf"\b{NETWORK_TOOL_PATTERN}\b", cmd_text or "", re.IGNORECASE):
        return False
    if not re.search(rf"\|\s*{SHELL_PATTERN}\b", cmd_text or "", re.IGNORECASE):
        return False
    # 含有外发数据包的行为不可豁免为安装脚本
    if EgressUploadHint_RE.search(cmd_text or ""):
        return False
    urls = _extract_urls(cmd_text)
    if not urls:
        return False

    trusted_domains = _configured_trusted_domains()
    for url in urls:
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            return False
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        if host == RAW_GITHUB_HOST:
            if _is_pinned_raw_github_url(url) or _is_known_raw_github_installer_url(url):
                continue
            return False
        if host in trusted_domains or any(host.endswith("." + domain) for domain in trusted_domains):
            continue
        return False
    return True


def _is_sensitive_payload_ref(ref: str) -> bool:
    """ 检查通过 curl 等工具向外上传的目标文件是否为高危密钥、配置文件（如 .env、id_rsa）。
    Args:
        ref (str): 挂载的文件路径字符串。
    Returns:
        bool: 匹配到敏感文件名返回 True。
    """
    normalized = _normalize_token(ref)
    return bool(normalized and SENSITIVE_REF_RE.search(normalized))


def _check_ecosystem_trust(cmd_text: str, context: dict[str, Any]) -> dict[str, Any] | None:
    """ 检查包管理器（如 npm, pip 等）调用时，是否使用了不受信任的自定义镜像源，防范恶意源依赖投毒。
    Args:
        cmd_text (str): 命令行。
        context (dict): 上下文。
    Returns:
        dict|None: 如果使用了恶意源返回阻塞或复核字典；安全则返回无。
    """
    if not PACKAGE_MANAGER_ALLOW_RE.search(cmd_text or ""):
        return None
    if PACKAGE_MANAGER_CUSTOM_SOURCE_RE.search(cmd_text or ""):
        risk = _extract_and_check_urls(cmd_text)
        if risk == 1:
            return _result(1, "Triggered block: package manager uses malicious custom source.", "BLOCK_PM_CUSTOM_SOURCE_MALICIOUS")
        return _result(2, "Review required: package manager uses custom source.", "REVIEW_PM_CUSTOM_SOURCE")
    if context.get("trust_profile") in {"developer", "enterprise"}:
        return _result(0, "Trusted package manager workflow.", "SAFE_ECOSYSTEM_TRUST")
    return None


def _check_data_exfiltration(cmd_text: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """ 探测命令是否包含数据外发意图，比如通过 curl 上传密钥文件，或通过 ping 夹带数据进行 ICMP 外发绕过防火墙。
    Args:
        cmd_text (str): 命令行。
        context (dict): 环境上下文信息。
    Returns:
        dict|None: 存在外发现象时根据外发地址的信任度和文件敏感度返回处理意见对象。
    """
    context = context or {}
    normalized_text = _normalize_command_for_detection(cmd_text)
    lower = normalized_text.lower()
    if not NETWORK_EGRESS_RE.search(lower):
        return None
    if not EgressUploadHint_RE.search(lower):
        return None
    risk = _extract_and_check_urls(cmd_text)
    payload_refs = _extract_egress_payload_refs(cmd_text)
    normalized_refs = [_normalize_payload_ref_path(ref) for ref in payload_refs]
    has_sensitive_ref = any(_is_sensitive_payload_ref(ref) for ref in payload_refs)
    if "ping" in lower and re.search(r"(?:^|\s)-p\s+[0-9a-f]{8,}\b", lower):
        ping_hosts = _extract_ping_hosts(cmd_text)
        if ping_hosts and all(_is_local_or_private_host(host) for host in ping_hosts):
            return _result(0, "Local/private ICMP payload diagnostic pattern allowed.", "SAFE_ICMP_LOCAL_DEBUG")
        return _result(1 if risk in {1, 2} else 2, "Potential ICMP data exfiltration pattern.", "BLOCK_EXFIL_ICMP")
    if has_sensitive_ref and risk in {1, 2}:
        return _result(1, "Triggered block: sensitive data egress to untrusted destination.", "BLOCK_EXFIL_SENSITIVE")
    if risk in {1, 2} and _is_dev_log_upload_allowed(normalized_refs, context):
        return _result(0, "Developer log upload from workspace/temp allowed.", "SAFE_DEV_LOG_UPLOAD")
    if risk in {1, 2}:
        return _result(2, "Review required: outbound upload-like data transfer.", "REVIEW_EXFIL_SUSPECTED")
    return None


def _check_stealth_background(cmd_text: str) -> dict[str, Any] | None:
    """ 检查命令是否使用了分离终端（nohup, setsid, tmux 等）来维持一个不被注销打断的隐蔽后台常驻进程（多用于木马持久化）。
    Args:
        cmd_text (str): 执行文本。
    Returns:
        dict|None: 如果捕获到非常规的后台运行特征，返回处理结果。
    """
    normalized_text = _normalize_command_for_detection(cmd_text)
    if not STEALTH_BACKGROUND_RE.search(normalized_text):
        return None
    if SAFE_DEV_BACKGROUND_RE.search(normalized_text):
        if _is_local_network_only(normalized_text):
            return _result(0, "Local dev background process allowed.", "SAFE_BACKGROUND_DEV_LOCAL")
        return _result(2, "Review required: background developer process.", "REVIEW_BACKGROUND_DEV")
    return _result(1, "Triggered block: unmanaged stealth/background process.", "BLOCK_STEALTH_BACKGROUND")


def _attach_decision_context(
    result: dict[str, Any],
    context: dict[str, Any],
    *,
    sandbox_downgraded: bool = False,
    egress_flags: list[str] | None = None,
) -> dict[str, Any]:
    """ 为输出的检测结果对象附加运行时的上下文信息与额外标记，方便上层系统或风控查看决策原因。
    Args:
        result (dict): 原扫描字典结果。
        context (dict): 系统当前环境上下文。
        sandbox_downgraded (bool): 表明是否因为当前是短暂沙箱环境而降低了风险评级。
        egress_flags (list): 是否疑似含有数据外泄（exfil）标记。
    Returns:
        dict[str, Any]: 扩展数据后的最终字典。
    """
    result["decision_context"] = {
        "agent_env": context.get("agent_env", DEFAULT_AGENT_ENV),
        "trust_profile_used": context.get("trust_profile", DEFAULT_TRUST_PROFILE),
        "sandbox_downgraded": sandbox_downgraded,
        "egress_flags": egress_flags or [],
    }
    return result


def _can_sandbox_downgrade(cmd_text: str) -> bool:
    """ 如果命令执行环境是临时沙箱（阅后即焚环境），评估该命令是否可以被放行（降级阻断级别）。
    像提权操作（sudo）或外发传输（curl POST）即使在沙箱中也不允许降级。
    Args:
        cmd_text (str): 需检查的命令。
    Returns:
        bool: 如果不包含特定严重高风险特征，允许降级时返回 True。
    """
    if NETWORK_EGRESS_RE.search(cmd_text or "") and EgressUploadHint_RE.search(cmd_text or ""):
        return False
    if re.search(r"\b(?:sudo|pkexec|doas|schtasks|sc\s+create|systemd|crontab|reg\s+add)\b", cmd_text or "", re.IGNORECASE):
        return False
    return True


def _collect_command_events(cmd_text: str, context: dict[str, Any]) -> list[dict[str, Any]]:
    """ 分析当前命令执行是否对系统产生了“落盘污染”动作（如下载了新文件、创建了解码脚本等）。这些动作路径将被收集并存入历史会话上下文。
    Args:
        cmd_text (str): 当前执行的命令。
        context (dict): 上下文信息。
    Returns:
        list[dict]: 提取出的带有污染标记（tainted）的落盘路径和事件行为列表。
    """
    events: list[dict[str, Any]] = []
    normalized_text = _normalize_command_for_detection(cmd_text)
    has_url = bool(re.search(r"https?://", normalized_text, re.IGNORECASE))
    url_risk = _extract_and_check_urls(cmd_text) if has_url else 0
    tainted_from_net = has_url and url_risk in {1, 2}
    write_script_tainted = tainted_from_net or bool(
        DECODE_HINT_RE.search(normalized_text) and re.search(rf"\|\s*{SHELL_PATTERN}\b", normalized_text, re.IGNORECASE)
    )

    for path in _extract_download_paths(cmd_text):
        events.append({"kind": "download", "path": path, "tainted": tainted_from_net})
    for path in _extract_script_write_paths(cmd_text):
        events.append({"kind": "write_script", "path": path, "tainted": write_script_tainted})
    if ARCHIVE_EXTRACT_RE.search(cmd_text or ""):
        events.append({"kind": "extract_archive", "path": str(context.get("cwd") or "."), "tainted": tainted_from_net})
    if DECODE_HINT_RE.search(cmd_text or "") and re.search(rf"\|\s*{SHELL_PATTERN}\b", cmd_text or "", re.IGNORECASE):
        events.append({"kind": "decode_exec", "path": "", "tainted": True})
    return events


def _find_tainted_path(paths: set[str], history: list[dict[str, Any]]) -> str:
    """ 在历史会话事件中比对，检查当前执行的路径列表里，是否有先前命令下载/创建的“污点（tainted）”文件。
    Args:
        paths (set): 本次需要执行的本地路径集合。
        history (list): 该会话历史保存的事件列表。
    Returns:
        str: 如果发现执行目标是曾经受污染的文件，返回该路径名称，否则返回空串。
    """
    tainted_paths = {str(item.get("path", "")) for item in history if item.get("tainted")}
    if not tainted_paths:
        return ""
    for path in paths:
        if path in tainted_paths:
            return path
    return ""


def _check_taint_execution_chain(
    cmd_text: str,
    context: dict[str, Any],
    history: list[dict[str, Any]],
    current_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """ 执行污点追踪验证：侦测跨命令的“Staged Execution（下载后执行）”。如果识别到当前执行的文件来源于不受信任的先前回话下载，则判定为高危连环利用。
    Args:
        cmd_text (str): 待检查命令。
        context (dict): 上下文。
        history (list): 历史事件记录。
        current_events (list): 本次新产生的事件记录（同条命令内先写后执行）。
    Returns:
        dict|None: 如果命中了被污染文件的执行链条，则返回相关阻断字典。
    """
    executed = _extract_executed_paths(cmd_text)
    sourced = _extract_shell_paths(SOURCE_PATH_RE, cmd_text)
    if not executed and not sourced:
        return None

    tainted_hit = _find_tainted_path(executed | sourced, history)
    if tainted_hit:
        if context.get("privileged"):
            return _result(1, "Triggered block: privileged execution of tainted staged file.", "BLOCK_TAINTED_CHAIN_PRIV")
        return _result(2, "Review required: staged file execution from untrusted source.", "REVIEW_TAINTED_CHAIN")

    staged_now = {str(e.get("path", "")) for e in (current_events or []) if e.get("kind") in {"download", "write_script"} and e.get("tainted")}
    if staged_now and any(path in staged_now for path in (executed | sourced)):
        if context.get("privileged"):
            return _result(1, "Triggered block: privileged same-command staged execution.", "BLOCK_TAINTED_CHAIN_PRIV")
        return _result(2, "Review required: same-command staged download/write and execution.", "REVIEW_TAINTED_CHAIN")

    for path in executed | sourced:
        if _is_workspace_or_temp_path(path, context):
            continue
        if _contains_var_or_substitution(path):
            return _result(2, "Review required: dynamic script path execution/source.", "REVIEW_DYNAMIC_SCRIPT_PATH")
    return None


def _command_name_matches(name: str, exact: set[str], prefixes: tuple[str, ...] = ()) -> bool:
    """ 检查被调用的底层工具名是否命中了被禁止执行的工具黑名单（如 wipefs 等物理磁盘操作命令）。
    Args:
        name (str): 提取出的命令基础名称。
        exact (set): 完全匹配的黑名单集合。
        prefixes (tuple): 前缀匹配的黑名单集合。
    Returns:
        bool: 命中黑名单时返回 True。
    """
    base = _normalize_token(name).split("/")[-1].split("\\")[-1].lower()
    return base in exact or any(base == p or base.startswith(p + ".") for p in prefixes)


def _has_flag(args: list[str], *flags: str) -> bool:
    """ 拆解参数集合，检查命令中是否明确声明了指定的敏感启动参数或短选项标志（如 netcat 的 -e 参数）。
    Args:
        args (list): 工具调用的参数列表。
        flags (str): 可变的需要检测的参数项。
    Returns:
        bool: 存在对应参数时返回 True。
    """
    wanted = set(flags)
    for arg in args:
        if arg in wanted:
            return True
        if arg.startswith("-") and not arg.startswith("--"):
            letters = set(arg[1:])
            if any(len(flag) == 2 and flag[1:] in letters for flag in wanted):
                return True
    return False


def _extract_and_check_urls(text: str) -> int:
    """ 从命令中提取 URL，与内部可信域名列表比对，并检查是否存在恶意的内网 SSRF 探针或 C2 远控 IP。
    Args:
        text (str): 扫描区文本。
    Returns:
        int: 风险分级。0(全可信且安全)、1(发现公认恶意域名或私有IP特征)、2(未知来源域名，存疑需复核)。
    """
    """
    return:
      0 = all urls look trusted
      1 = malicious/high-risk url found
      2 = unknown/untrusted or parse ambiguity
    """
    urls = re.findall(r"https?://[^\s\"'>|]+", text or "")
    if not urls:
        return 2

    trusted_domains = _configured_trusted_domains()
    for url in urls:
        try:
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.hostname or ""
            hostname = hostname.lower()

            if hostname in {"169.254.169.254", "100.100.100.200"}:
                return 1
            if MALICIOUS_HOST_HINT_RE.search(hostname):
                return 1
            if _is_local_or_private_host(hostname):
                if parsed.port and parsed.port < 1024 and hostname != "localhost":
                    return 2
                continue
            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
                return 1

            if hostname == RAW_GITHUB_HOST:
                if _is_pinned_raw_github_url(url):
                    continue
                return 2

            if hostname in trusted_domains:
                continue
            if any(hostname.endswith("." + trusted) for trusted in trusted_domains):
                continue

            return 2
        except Exception:
            return 2

    return 0


def _check_sensitive_redirect_text(cmd_text: str) -> dict[str, Any] | None:
    """ 检查命令是否利用 Shell 输出重定向符号（> 或 >>）非法覆写核心系统文件（如 /etc/passwd）来实现篡改或提权。
    Args:
        cmd_text (str): 包含重定向的命令行文本。
    Returns:
        dict|None: 违规覆写目标时返回相应的阻断状态字典。
    """
    for match in REDIRECT_TARGET_RE.finditer(cmd_text or ""):
        target = _normalize_token(match.group(1))
        if BLOCK_WRITE_PATHS.match(target):
            return _result(
                1,
                "Triggered block: redirect writes to sensitive path.",
                "BLOCK_REDIRECT_SENSITIVE",
            )
        if REVIEW_WRITE_PATHS.match(target):
            return _result(
                2,
                "Review required: redirect writes to persistence-related path.",
                "REVIEW_REDIRECT_PERSISTENCE",
            )
    return None


def _has_dd_raw_disk_write(cmd_text: str) -> bool:
    """ 检查是否存在使用 `dd` 命令通过 `of=/dev/...` 形式直接向磁盘底层块设备覆写数据的物理破坏意图。
    Args:
        cmd_text (str): 原始命令。
    Returns:
        bool: 如果命中了对物理盘或分区底层块设备的写操作，返回 True。
    """
    return bool(DD_RAW_DISK_RE.search(cmd_text or ""))


def _infer_shell_type_from_command(cmd_text: str) -> str:
    """ 通过分析命令中包含的命令关键词语法，探测并猜测该指令隶属于 Bash 还是 PowerShell 运行环境。
    Args:
        cmd_text (str): 输入命令内容。
    Returns:
        str: 猜测出的执行器名称（'bash', 'powershell', 'cmd' 等），若无法断定则为空。
    """
    text = _normalize_command_for_detection(cmd_text)

    if re.search(r"\bcmd(?:\.exe)?\s+/c\b", text, re.IGNORECASE):
        return "cmd"

    has_bash = bool(BASH_HINT_RE.search(text))
    has_windows = bool(WINDOWS_HINT_RE.search(text))

    if has_bash and not has_windows:
        return "bash"
    if has_windows and not has_bash:
        return "powershell"

    if has_bash and has_windows:
        if re.search(r"\b(?:bash|sh|zsh)\b", text, re.IGNORECASE):
            return "bash"
        if re.search(r"\b(?:powershell|pwsh|cmd(?:\.exe)?)\b", text, re.IGNORECASE):
            return "powershell"

    return ""


def _check_windows_specific_risks(cmd_text: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """ 专门处理 Windows 下的（PowerShell/cmd）安全威胁逻辑检测。
    包含且不限于：IEX 下载执行内存马、关闭防火墙与杀软、破坏 BCD 启动菜单、创建服务以及利用 certutil 隐蔽下载等行为。
    Args:
        cmd_text (str): 执行用指令。
        context (dict): 补充的环境配置。
    Returns:
        dict|None: 命中 Windows 的独享检测规则将返回对应结果字典。
    """
    context = context or {}
    lower = (cmd_text or "").lower()

    redirect_risk = _check_sensitive_redirect_text(cmd_text)
    if redirect_risk:
        return redirect_risk

    if re.search(r"\b(iex|invoke-expression)\b", lower) and re.search(
        r"(downloadstring|invoke-restmethod|invoke-webrequest|iwr)\b", lower
    ):
        risk = _extract_and_check_urls(cmd_text)
        if risk == 1:
            return _result(
                1,
                "Triggered block: malicious PowerShell download-and-execute.",
                "BLOCK_PWSH_MALICIOUS_NET",
            )
        return _result(
            2,
            "Review required: PowerShell download and execute unknown URL.",
            "REVIEW_PWSH_NET_EXEC",
        )

    # Allow agent to bypass execution policy for its own process scope
    if re.search(r"\bset-executionpolicy\b", lower) and not re.search(r"-scope\s+process\b", lower):
        return _result(
            2,
            "Review required: changing global PowerShell execution policy.",
            "REVIEW_PWSH_EXEC_POLICY",
        )

    if re.search(r"\b(?:invoke-webrequest|iwr)\b", lower) and re.search(r"-outfile\b", lower):
        risk = _extract_and_check_urls(cmd_text)
        targets = _extract_download_paths(cmd_text)
        if risk == 1:
            return _result(1, "Triggered block: malicious PowerShell remote download.", "BLOCK_PWSH_DOWNLOAD_MALICIOUS")
        if any(BLOCK_WRITE_PATHS.match(_normalize_token(t)) for t in targets):
            return _result(2, "Review required: PowerShell download targets sensitive path.", "REVIEW_PWSH_DOWNLOAD")
        if targets and all(_is_workspace_or_temp_path(t, context) for t in targets):
            return _result(0, "PowerShell remote download to workspace/temp only.", "SAFE_PWSH_DOWNLOAD_ONLY")
        return _result(2, "Review required: downloading remote file via PowerShell.", "REVIEW_PWSH_DOWNLOAD")

    if re.search(
        r"\breg\s+(add|delete)\s+hklm[\\/]+software[\\/]+microsoft[\\/]+windows[\\/]+currentversion[\\/]+run\b",
        lower,
    ):
        return _result(
            1,
            "Triggered block: modifying Windows autostart registry.",
            "BLOCK_WIN_REG_AUTOSTART",
        )

    if re.search(
        r"\breg\s+add\s+hklm[\\/]+software[\\/]+microsoft[\\/]+windows nt[\\/]+currentversion[\\/]+winlogon\b.*\buserinit\b",
        lower,
    ):
        return _result(
            1,
            "Triggered block: tampering Winlogon Userinit.",
            "BLOCK_WIN_BOOT_TAMPER",
        )

    if "schtasks" in lower and "/create" in lower:
        return _result(
            1,
            "Triggered block: scheduled task persistence.",
            "BLOCK_WIN_SCHTASK_PERSIST",
        )

    if re.search(r"\bsc\s+create\b[^\n;|&]*\bbinpath\s*=", lower):
        return _result(
            1,
            "Triggered block: Windows service persistence.",
            "BLOCK_WIN_SERVICE_PERSIST",
        )

    if re.search(
        r"\bnet\s+user\b[^\n;|&]*/add\b[^\n;|&]*&&[^\n;|&]*\bnet\s+localgroup\s+administrators\b[^\n;|&]*/add\b",
        lower,
    ):
        return _result(
            1,
            "Triggered block: privilege grant to Administrators.",
            "BLOCK_WIN_PRIV_GRANT",
        )

    if re.search(r"\b(?:rd|del)\b[^\n;|&]*c:[\\/]+windows[\\/]+system32", lower):
        return _result(
            1,
            "Triggered block: deleting Windows core path.",
            "BLOCK_WIN_DESTRUCTIVE_DELETE",
        )

    if re.search(
        r"remove-item[^\n;|&]*-path\s+\"?c:[\\/]+(?:windows|users[\\/]+public)[^\n;|&]*-recurse[^\n;|&]*-force",
        lower,
    ):
        return _result(
            1,
            "Triggered block: destructive Remove-Item on sensitive path.",
            "BLOCK_WIN_DESTRUCTIVE_DELETE",
        )

    if re.search(r"\bnetsh\s+advfirewall\s+set\s+allprofiles\s+state\s+off\b", lower):
        return _result(
            1,
            "Triggered block: disabling firewall.",
            "BLOCK_WIN_DISABLE_FIREWALL",
        )

    if re.search(
        r"\b(?:set-mppreference\s+-disablerealtimemonitoring|add-mppreference\s+-exclusionpath)\b",
        lower,
    ):
        return _result(
            2,
            "Review required: changing defender security policy.",
            "REVIEW_WIN_SECURITY_POLICY",
        )

    if re.search(r"\b(?:wbadmin\s+delete\s+catalog|cipher\s+/w:)\b", lower):
        return _result(
            1,
            "Triggered block: backup destroy operation.",
            "BLOCK_WIN_BACKUP_DESTROY",
        )

    if re.search(
        r"\bbcdedit\b[^\n;|&]*(?:bootstatuspolicy|recoveryenabled|displaybootmenu|safeboot|nx|testsigning)",
        lower,
    ):
        return _result(
            1,
            "Triggered block: boot configuration tampering.",
            "BLOCK_WIN_BOOT_TAMPER",
        )

    if re.search(r"\b(?:certutil|bitsadmin)\b", lower) and "http" in lower:
        risk = _extract_and_check_urls(cmd_text)
        targets = _extract_download_paths(cmd_text)
        if re.search(r"&&\s*(?:start|cmd\s+/c|powershell\b)", lower):
            return _result(
                1 if risk == 1 else 2,
                "Download-and-exec chain via certutil/bitsadmin.",
                "BLOCK_WIN_DL_EXEC" if risk == 1 else "REVIEW_WIN_DL_EXEC",
            )
        if risk == 1:
            return _result(1, "Triggered block: malicious certutil/bitsadmin download.", "BLOCK_WIN_DOWNLOAD_MALICIOUS")
        if targets and all(_is_workspace_or_temp_path(t, context) for t in targets):
            return _result(0, "Windows remote download to workspace/temp only.", "SAFE_WIN_DOWNLOAD_ONLY")
        return _result(
            2,
            "Review required: remote binary download on Windows.",
            "REVIEW_WIN_DOWNLOAD",
        )

    if re.search(r"\bformat-volume\b|\bformat\s+[a-z]:(?:\s|$)|\bvssadmin\s+delete\s+shadows\b", lower):
        return _result(
            1,
            "Triggered block: destructive Windows disk/backup operation.",
            "BLOCK_WIN_DESTRUCTIVE",
        )

    if "diskpart" in lower and re.search(r"\bclean\b", lower):
        return _result(
            1,
            "Triggered block: destructive diskpart clean operation.",
            "BLOCK_WIN_DISKPART_CLEAN",
        )

    return None


def _node_text(node: Any, script: str) -> str:
    """ 从 Tree-sitter AST 解析器捕获的语法节点中，定位对应的原始脚本字符串并切片截取出来。
    Args:
        node (Any): AST 对象节点。
        script (str): 解析该节点的源字符串文本。
    Returns:
        str: 节点代表的实际代码片段。
    """
    if not node:
        return ""
    return script[node.start_byte: node.end_byte]


def _first_command_name_and_args(node: Any, script: str) -> tuple[str, list[str]]:
    """ 遍历并解析 AST 中的命令层级节点，分离出它具体的执行名称（可执行程序）和对应的传入参数列表，忽略环境变量赋值前置段。
    Args:
        node (Any): Bash AST 分支中的 command 类型节点。
        script (str): 命令原文。
    Returns:
        tuple: 第一个元素是程序的名称字符串，第二个元素是其所带的参数列表。
    """
    tokens = []
    ignore = {"|", "||", "&", "&&", ";", ";;", "(", ")", "{", "}", "\n"}

    for child in node.children:
        text = _normalize_token(_node_text(child, script))
        if text and text not in ignore:
            tokens.append(text)

    index = 0
    assign_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
    while index < len(tokens) and assign_re.match(tokens[index]):
        index += 1

    if index >= len(tokens):
        return "", []

    return tokens[index], tokens[index + 1:]


def _check_bash_exec_chain_text(cmd_text: str) -> dict[str, Any] | None:
    """ 迭代纯文本层面的 Bash “网络注入执行”模式规则（例如进程替换 `bash <(curl xxx)` ）。
    Args:
        cmd_text (str): 标准化后的执行命令文本。
    Returns:
        dict|None: 如果命中了组合型远程执行规则块，则返回对应的安全拦截策略和提示。
    """
    normalized_text = _normalize_command_for_detection(cmd_text)
    for pattern, review_id, block_id, desc in BASH_EXEC_CHAIN_TEXT_RULES:
        if re.search(pattern, normalized_text, re.IGNORECASE):
            risk = _extract_and_check_urls(cmd_text)
            if risk == 1:
                return _result(1, f"Triggered block: malicious {desc}.", block_id)
            if risk == 2:
                return _result(2, f"Review required: {desc}.", review_id)

    return None


def _check_bash_command_node(node: Any, script: str) -> dict[str, Any] | None:
    """ 在 AST 拆解出独立的命令执行对象后，对其特定用法（例如 netcat 是否带有 -e 反弹参数，chmod 是否试图开启特权执行位等）进行分析。
    Args:
        node (Any): AST Command 节点。
        script (str): 解析脚本源文本。
    Returns:
        dict|None: 若存在危险行为，返回拦截提示字典。
    """
    cmd_name, args = _first_command_name_and_args(node, script)
    raw = _node_text(node, script)
    cmd_name_lower = cmd_name.lower()

    if _command_name_matches(cmd_name_lower, {"nc", "netcat"}) and _has_flag(args, "-e", "-c"):
        return _result(1, "Triggered block: nc/netcat with exec flag.", "BLOCK_NETCAT_EXEC")

    if _command_name_matches(cmd_name_lower, BANNED_EXACT, BANNED_PREFIX):
        return _result(1, f"Triggered block: banned tool {cmd_name}.", "BLOCK_BANNED_TOOL")

    if cmd_name_lower in {"chmod", "chown"} and any(
        re.search(r"(^|[^0-9])(47(?:55|77))(?:[^0-9]|$)|\bu\+s\b", a)
        for a in args
    ):
        return _result(1, "Triggered block: trying to set SUID bit.", "BLOCK_SUID")

    if cmd_name_lower in {"docker", "kubectl", "sudo"}:
        if re.search(r"\b(?:sh|bash|zsh)\s+-c\b", raw, re.IGNORECASE) and _contains_var_or_substitution(raw):
            return _result(
                2,
                "Potential risk: wrapped command executes dynamic payload.",
                "REVIEW_WRAPPER_DYNAMIC",
            )

    if cmd_name_lower == "tee":
        for arg in args:
            if arg.startswith("-"):
                continue
            target = _normalize_token(arg)
            if BLOCK_WRITE_PATHS.match(target):
                return _result(1, "Triggered block: tee writes to sensitive path.", "BLOCK_TEE_SENSITIVE")
            if REVIEW_WRITE_PATHS.match(target):
                return _result(2, "Review required: tee writes to persistence-related path.", "REVIEW_TEE_PERSISTENCE")

    return None


def _check_bash_pipeline(pipeline: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """ 检测 Bash 管道符（|）构成的数据流控制是否属于网络远程恶意利用链。最典型的是 `curl xx | bash` 无本地落地文件加载内存木马。
    Args:
        pipeline (str): 抽取的管道流转代码段。
        context (dict): 可选补充环境。
    Returns:
        dict|None: 若网络源不受信任，则返回被拦截风险信息对象。
    """
    context = context or {}
    if re.search(rf"\b{NETWORK_TOOL_PATTERN}\b", pipeline, re.IGNORECASE) and re.search(
        rf"\|\s*{SHELL_PATTERN}\b", pipeline, re.IGNORECASE
    ):
        if _is_dev_install_pipeline_allowed(pipeline, context):
            return _result(0, "Trusted developer installer pipeline allowed.", "SAFE_DEV_INSTALL_PIPE")
        risk = _extract_and_check_urls(pipeline)
        if risk == 1:
            return _result(1, "Triggered block: malicious IP/SSRF piped to shell.", "BLOCK_PIPE_MALICIOUS")
        if risk == 2:
            return _result(2, "Review required: unknown domain piped to shell.", "REVIEW_PIPE_NET_SHELL")

    if re.search(rf"\|\s*{SHELL_PATTERN}\b", pipeline, re.IGNORECASE) and re.search(
        r"\b(base64|openssl|xxd)\b.*(?:-d|--decode|-r)", pipeline, re.IGNORECASE
    ):
        risk = _extract_and_check_urls(pipeline)
        if risk == 1 or re.search(rf"\b{NETWORK_TOOL_PATTERN}\b", pipeline, re.IGNORECASE):
            return _result(1, "Triggered block: decoded payload piped to shell from untrusted source.", "BLOCK_PIPE_DECODE_NET_SHELL")
        return _result(2, "Review required: decoded content piped to shell.", "REVIEW_PIPE_DECODE_SHELL")

    return None


def _walk_bash_tree(node: Any, script: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """ 递归遍历 Tree-sitter 生成的整个 Bash 抽象语法树（AST），并根据节点类型触发上述的具体细分检测规则进行深层分析。
    Args:
        node (Any): 本级要解析的 AST 节点。
        script (str): 被解构的全篇命令行。
        context (dict): 检测上下文参数。
    Returns:
        dict|None: 只要在此树分支中捕获到任何一条违规行为，立即将其阻断或报警信息透传返回。
    """
    context = context or {}
    if not node:
        return None

    if node.type == "command":
        result = _check_bash_command_node(node, script)
        if result:
            return result

    elif node.type == "pipeline":
        result = _check_bash_pipeline(_node_text(node, script), context)
        if result:
            return result

    elif node.type in {"file_redirect", "redirected_statement"}:
        result = _check_sensitive_redirect_text(_node_text(node, script))
        if result:
            return result

    for child in node.children:
        child_result = _walk_bash_tree(child, script, context)
        if child_result:
            return child_result

    return None


def _is_static_shell_payload(text: str) -> bool:
    """ 检查交给解释器（例如 `bash -c`）处理的载荷内容是否属于写死的静态字符串，没有任何被环境变量或进程替换所污染改变的可能。
    Args:
        text (str): 被执行文本。
    Returns:
        bool: 全由硬编码字符串组成时返回 True。
    """
    if _contains_var_or_substitution(text):
        return False
    return bool(re.search(r"\b(?:bash|sh|zsh)\b[^\n;|&]*\s-c\s+['\"][^'\"]+['\"]", text, re.IGNORECASE))


def _is_dynamic_awk_system(text: str) -> bool:
    """ 检测由于使用外部变量拼接导致 awk system() 系统命令被沙箱逃逸（如调用 $ENVIRON 或利用反引号闭合注入）的风险情况。
    Args:
        text (str): 使用到 awk 命令的语句。
    Returns:
        bool: 带有外部拼接逃逸可能时返回 True。
    """
    if not re.search(r"\bawk\b[^\n;|&]*system\s*\(", text or "", re.IGNORECASE):
        return False
    return bool(re.search(r"ENVIRON|\$|`|\$\(|\{", text or ""))


def _permission_targets(cmd_text: str) -> list[str]:
    """ 过滤、剥离参数配置项后，获取被 chmod 和 chown 指令所具体操作指向的所有实际目标文件/目录对象。
    Args:
        cmd_text (str): 正在执行变更权限的语句文本。
    Returns:
        list[str]: 该命令更改了权限或归属权的具体目标路径列表。
    """
    raw = re.findall(r"\b(?:chmod|chown)\b[^\n;|&]*", cmd_text or "", re.IGNORECASE)
    if not raw:
        return []
    tokens = re.findall(r"(\"[^\"]+\"|'[^']+'|[^\s]+)", raw[0])
    result: list[str] = []
    for token in tokens[1:]:
        value = _normalize_token(token)
        if value and not value.startswith("-") and not re.fullmatch(r"[0-7]{3,4}|[ugoa][=+-].*", value):
            result.append(value)
    return result


def _check_broad_permission_context(cmd_text: str, context: dict[str, Any]) -> dict[str, Any] | None:
    """ 杜绝对诸如 /etc、/root 这类关键核心系统目录进行全放开的粗暴提权尝试（如 chmod 777）。
    Args:
        cmd_text (str): 命令行。
        context (dict): 上下文信息，提供其豁免检测目录区间。
    Returns:
        dict|None: 若命中了不合规的越界或最高权限改变，则返回拦截提示。
    """
    if not re.search(r"\bchmod\b[^\n;|&]*(?:\b777\b|a\+rwx)", cmd_text or "", re.IGNORECASE):
        return None
    targets = _permission_targets(cmd_text)
    if any(re.search(r"^(?:/|/etc|/root|/usr)(?:$|/)", t.lower()) for t in targets):
        return _result(1, "Triggered block: broad permission on core path.", "BLOCK_CORE_PERMISSION_OPEN")
    if not targets:
        return _result(2, "Review required: broad permission change.", "REVIEW_BROAD_PERMISSION")
    if any(_contains_var_or_substitution(t) for t in targets):
        return _result(2, "Review required: dynamic broad permission target.", "REVIEW_BROAD_PERMISSION")
    if all(_is_workspace_or_temp_path(t, context) for t in targets):
        return _result(0, "Broad permission change limited to workspace/temp.", "SAFE_BROAD_PERMISSION_WORKSPACE")
    return _result(2, "Review required: broad permission change.", "REVIEW_BROAD_PERMISSION")


def _analyze_windows_command(cmd_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """ Windows（cmd/powershell）环境安全威胁扫描的核心路由节点。
    Args:
        cmd_text (str): 要分析的命令。
        context (dict): 上下文环境。
    Returns:
        dict: 若检测存在 Windows 环境高危指令则拦截，否则视为默认安全放行。
    """
    win_risk = _check_windows_specific_risks(cmd_text, context)
    if win_risk:
        return win_risk

    return _result(0, "Windows command has no obvious security risk.", "SAFE_WINDOWS_DEFAULT")


def _analyze_bash_command(cmd_text: str, cmd_bytes: bytes, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """ Linux Bash 环境安全扫描的核心入口与编排器。综合负责正则扫描、Python/Nodejs 等解释器语言嵌入恶意调用、及最后交由 AST 树精确溯源拦截等深层扫描流程。
    Args:
        cmd_text (str): UTF8 文本形式原始命令。
        cmd_bytes (bytes): 用于传递给 Tree-sitter 引擎的字节流。
        context (dict): 上下文环境。
    Returns:
        dict: 安全引擎判断反馈，不触发拦截则为安全放行结果。
    """
    context = context or {}
    normalized_text = _normalize_command_for_detection(cmd_text)
    lower = normalized_text.lower()

    if _has_dd_raw_disk_write(cmd_text):
        return _result(1, "Triggered block: dd writes to raw disk.", "BLOCK_DD_RAW_DISK")

    if re.search(r"\brm\b", lower) and re.search(
        r"-(?:[^\s]*r[^\s]*f|[^\s]*f[^\s]*r)", lower
    ) and re.search(r"(?:^|[\s])(?:/\*?|/etc|/root|/usr)(?:$|[\s])", lower):
        return _result(1, "Triggered block: recursive force delete on core path.", "BLOCK_RM_RF_CORE")

    if re.search(r"\btar\b[^\n;|&]*--checkpoint-action\s*=\s*exec", lower):
        return _result(1, "Triggered block: tar checkpoint exec injection.", "BLOCK_TAR_EXEC")

    if re.search(
        rf"\b(?:bash|sh|zsh)\b[^\n|&]*\s-c\b[^\n|&]*\b{NETWORK_TOOL_PATTERN}\b[^\n|&]*\|\s*(?:sh|bash|zsh)\b",
        lower,
    ):
        if _is_dev_install_pipeline_allowed(cmd_text, context):
            return _result(0, "Trusted developer installer pipeline allowed.", "SAFE_DEV_INSTALL_PIPE")
        risk = _extract_and_check_urls(cmd_text)
        if risk == 0 and _is_local_network_only(cmd_text):
            return _result(0, "Local loopback/private shell-c pipeline allowed for dev testing.", "SAFE_LOCAL_NETPIPE")
        return _result(
            1 if risk == 1 else 2,
            "Inline shell -c download execution chain.",
            "BLOCK_SHELLC_NETPIPE" if risk == 1 else "REVIEW_SHELLC_NETPIPE",
        )

    if re.search(r"\bpython(?:3)?\b", lower) and re.search(
        r"os\.system\s*\(|subprocess\.", normalized_text
    ) and re.search(rf"\b{NETWORK_TOOL_PATTERN}\b", lower):
        risk = _extract_and_check_urls(cmd_text)
        return _result(
            1 if risk == 1 else 2,
            "Python download-and-run chain.",
            "BLOCK_PY_NET_MALICIOUS" if risk == 1 else "REVIEW_PY_NETPIPE",
        )

    if re.search(r"\bpython(?:3)?\b", lower) and re.search(
        r"\b(?:exec|eval|compile|runpy|importlib|pickle\.loads|ctypes\.cdll|os\.exec[a-z]*)\b",
        lower,
    ):
        return _result(2, "Review required: Python dynamic execution surface.", "REVIEW_PY_DYNAMIC_EXEC")

    if re.search(r"\bnode\b", lower) and re.search(
        r"\b(?:child_process\.(?:exec|spawn|execfile)|vm\.runin|buffer\.from\s*\([^)]*base64|eval\s*\()",
        lower,
    ):
        return _result(2, "Review required: Node dynamic execution surface.", "REVIEW_NODE_DYNAMIC_EXEC")

    if re.search(r"\b(?:pwsh|powershell)\b", lower) and re.search(
        r"(?:-encodedcommand|frombase64string|invoke-expression|iex)",
        lower,
    ):
        return _result(2, "Review required: PowerShell encoded/dynamic execution.", "REVIEW_PWSH_DYNAMIC_EXEC")

    if re.search(r"\bpython(?:3)?\b", lower) and re.search(
        r"os\.system\s*\(\s*input\s*\(\s*\)\s*\)", lower
    ):
        return _result(
            2,
            "Review required: interpreter execution driven by input().",
            "REVIEW_INTERPRETER_INPUT_EXEC",
        )

    if re.search(r"\beval\b", lower) and _contains_var_or_substitution(cmd_text):
        return _result(2, "Review required: dynamic eval execution.", "REVIEW_DYNAMIC_EVAL")

    if re.search(r"\b(?:bash|sh|zsh)\s*<\(", lower):
        return _result(2, "Review required: process substitution execution.", "REVIEW_PROCESS_SUB_EXEC")

    if re.search(r"\b(?:bash|sh|zsh)\b[^\n;|&]*\s-c\b", lower):
        if _contains_var_or_substitution(cmd_text):
            return _result(2, "Review required: shell -c dynamic payload.", "REVIEW_DYNAMIC_SHELL_PAYLOAD")
        if _is_static_shell_payload(cmd_text):
            return _result(0, "shell -c runs static literal payload.", "SAFE_STATIC_SHELL_PAYLOAD")

    if re.search(r"\bxargs\b[^\n;|&]*(?:sh|bash|zsh)\b", lower):
        if _contains_var_or_substitution(cmd_text) or "{}" in cmd_text:
            return _result(2, "Review required: xargs drives dynamic shell execution.", "REVIEW_XARGS_SHELL")
        return _result(0, "xargs shell invocation is static literal.", "SAFE_XARGS_LITERAL_SHELL")

    if re.search(r"\bawk\b[^\n;|&]*system\s*\(", lower):
        if _is_dynamic_awk_system(cmd_text):
            return _result(2, "Review required: awk system() execution.", "REVIEW_AWK_SYSTEM")
        return _result(0, "awk system() with static literal command.", "SAFE_AWK_STATIC_SYSTEM")

    broad_permission = _check_broad_permission_context(cmd_text, context)
    if broad_permission:
        return broad_permission

    if re.search(r"\bchown\b[^\n;|&]*\s-r\b", lower):
        targets = _permission_targets(cmd_text)
        if any(re.search(r"^(?:/|/etc|/root|/usr)(?:$|/)", t.lower()) for t in targets):
            return _result(1, "Triggered block: recursive ownership change on core path.", "BLOCK_OWNERSHIP_CORE")
        if targets and all(_is_workspace_or_temp_path(t, context) for t in targets):
            return _result(0, "Recursive ownership change limited to workspace/temp.", "SAFE_OWNERSHIP_WORKSPACE")
        return _result(2, "Review required: recursive ownership change.", "REVIEW_OWNERSHIP_RECURSIVE")

    redirect_risk = _check_sensitive_redirect_text(cmd_text)
    if redirect_risk:
        return redirect_risk

    exec_chain_risk = _check_bash_exec_chain_text(cmd_text)
    if exec_chain_risk:
        return exec_chain_risk

    if not HAS_TREE_SITTER_BASH:
        return _result(0, "Bash AST engine missing; text rules found no high-risk pattern.", "SAFE_BASH_TEXT_ONLY")

    try:
        parser = Parser(Language(tree_sitter_bash.language()))
        tree = parser.parse(cmd_bytes)
    except Exception as exc:
        LOGGER.exception("Bash AST parse failed for command: %s", cmd_text)
        return _result(
            2,
            f"Bash AST parse exception: {type(exc).__name__}",
            "REVIEW_AST_PARSE_EXCEPTION",
        )

    tree_result = _walk_bash_tree(tree.root_node, cmd_text, context)
    if tree_result:
        return tree_result

    if tree.root_node.has_error:
        return _result(2, "Bash AST syntax error.", "REVIEW_BASH_AST_ERROR")

    return _result(0, "Bash command has no obvious security risk.", "SAFE_BASH_DEFAULT")


def _check_global_ecosystem(cmd_text: str, context: dict[str, Any]) -> EngineResult | None:
    """ 全局拦截调用：防范 npm/pip 包管理器的恶意外部源劫持和投毒。
    Args:
        cmd_text (str): 判断目标。
        context (dict): 上下文。
    Returns:
        EngineResult|None: 返回检测策略判定结果。
    """
    return _check_ecosystem_trust(cmd_text, context)


def _check_global_exfiltration(cmd_text: str, context: dict[str, Any]) -> EngineResult | None:
    """ 全局拦截调用：分析网络外发行为，捕获向不受信 IP 窃发敏感密码/配置文件的高危操作。
    Args:
        cmd_text (str): 检测目标。
        context (dict): 环境数据。
    Returns:
        EngineResult|None: 存在严重外发风险则阻断。
    """
    return _check_data_exfiltration(cmd_text, context)


def _check_global_background(cmd_text: str, _: dict[str, Any]) -> EngineResult | None:
    """ 全局拦截调用：拦截采用 nohup/tmux 方式启动未经授权且脱离管理的持久化后台（木马）驻留进程。
    Args:
        cmd_text (str): 检测目标。
        _ (dict): 此项未使用。
    Returns:
        EngineResult|None: 隐蔽后台运行时阻断。
    """
    return _check_stealth_background(cmd_text)


def _check_global_dd_raw_disk(cmd_text: str, _: dict[str, Any]) -> EngineResult | None:
    """ 全局拦截调用：封锁利用 dd 命令等途径直接暴力粉碎重写磁盘卷底层数据。
    Args:
        cmd_text (str): 监测目标。
        _ (dict): 此项未使用。
    Returns:
        EngineResult|None: 含有底层抹除企图时阻断。
    """
    if _has_dd_raw_disk_write(cmd_text):
        return _result(1, "Triggered block: dd writes to raw disk.", "BLOCK_DD_RAW_DISK")
    return None


def _check_global_rm_rf_core(cmd_text: str, _: dict[str, Any]) -> EngineResult | None:
    """ 全局拦截调用：阻断如 `rm -rf /etc` 或 `rm -rf /` 等物理摧毁操作系统级关键数据目录的行为。
    Args:
        cmd_text (str): 检测对象。
        _ (dict): 此项未使用。
    Returns:
        EngineResult|None: 强毁动作阻断状态报告。
    """
    lower = cmd_text.lower()
    if re.search(r"\brm\b", lower) and re.search(
        r"-(?:[^\s]*r[^\s]*f|[^\s]*f[^\s]*r)", lower
    ) and re.search(r"(?:^|[\s])(?:/\*?|/etc|/root|/usr)(?:$|[\s])", lower):
        return _result(1, "Triggered block: recursive force delete on core path.", "BLOCK_RM_RF_CORE")
    return None


def _check_global_redirect(cmd_text: str, _: dict[str, Any]) -> EngineResult | None:
    """ 全局拦截调用：封堵试图用重定向符把木马脚本直接植入并覆写（>>）到计划任务等开机自启系统文件中的兜底护城河。
    Args:
        cmd_text (str): 源字符。
        _ (dict): 此项未使用。
    Returns:
        EngineResult|None: 越权覆写直接拦截。
    """
    return _check_sensitive_redirect_text(cmd_text)


def _check_global_exec_chain(cmd_text: str, _: dict[str, Any]) -> EngineResult | None:
    """ 全局拦截调用：匹配各种直接在内存执行无本地文件落盘（无文件攻击/注入执行）的联合长后门加载命令。
    Args:
        cmd_text (str): 测试参数。
        _ (dict): 此项未使用。
    Returns:
        EngineResult|None: 命中网络连接执行链直接阻断。
    """
    return _check_bash_exec_chain_text(cmd_text)


# 对接上述各个全局通用的“跨平台防御策略函数”的调用路由表。
GLOBAL_RULE_CHECKERS: tuple[RuleChecker, ...] = (
    _check_global_ecosystem,
    _check_global_exfiltration,
    _check_global_background,
    _check_global_dd_raw_disk,
    _check_global_rm_rf_core,
    _check_global_redirect,
    _check_global_exec_chain,
)


def _run_global_rules(cmd_text: str, context: dict[str, Any]) -> EngineResult | None:
    """ 引擎调用此方法，按顺序逐一应用“跨平台”的高危全局防御规则，保证哪怕底层环境无法判定，最基本的安全底线也不会失守。
    Args:
        cmd_text (str): 检测请求的原内容。
        context (dict): 上下文环境变量字典。
    Returns:
        EngineResult|None: 一旦捕获任何首个越界风险，直接向上级返回拦截裁定，退出该检测轮次。
    """
    for checker in GLOBAL_RULE_CHECKERS:
        risk = checker(cmd_text, context)
        if risk:
            return risk
    return None


def _resolve_shell_type(cmd_info: dict[str, Any], cmd_text: str) -> str:
    """ 根据外部传入的已知运行类型字段或引擎内部自行分析出的命令特征，敲定这句命令需要转交哪类底层扫描器（bash或windows）。
    Args:
        cmd_info (dict): 带有外部定义信息的主装载内容。
        cmd_text (str): 待扫描文本内容。
    Returns:
        str: 确定的执行壳名称（如 bash 或是 powershell）。
    """
    shell_type = str(cmd_info.get("shell_type", "")).lower().strip()
    if shell_type:
        return shell_type
    inferred = _infer_shell_type_from_command(cmd_text)
    if inferred:
        return inferred
    return "bash"


def _analyze_by_shell_type(
    shell_type: str,
    cmd_text: str,
    cmd_bytes: bytes,
    context: dict[str, Any],
) -> EngineResult:
    """ 按照先前判断好的底层解释器环境种类，将其分流给能处理对应生态特有威胁逻辑（如 Windows 的 Registry 读写或 Linux 的 Bash AST 解析）的专属处理函数。
    Args:
        shell_type (str): 检测平台种类标签。
        cmd_text (str): 要处理的文本形式命令。
        cmd_bytes (bytes): 命令的字节化形态（主要提供给 Tree-sitter 使用）。
        context (dict): 环境。
    Returns:
        EngineResult: 各平台分流检测之后返回的判定对象。
    """
    if shell_type in {"powershell", "pwsh", "cmd"}:
        return _analyze_windows_command(cmd_text, context)
    if shell_type in {"bash", "sh", "zsh"}:
        return _analyze_bash_command(cmd_text, cmd_bytes, context)
    return _result(2, "Unknown shell type; review required.", "REVIEW_UNKNOWN_SHELL_TYPE")


def _finalize_engine_result(
    result: EngineResult,
    cmd_text: str,
    context: dict[str, Any],
    session_id: str,
    current_events: list[dict[str, Any]],
) -> EngineResult:
    """ 在结束整个深层与特有扫描后，在此汇总所有历史记录存入库中，并针对特殊的降级沙盒执行模式判定其是否符合被放宽准许（即把阻断降维为仅提示异常）。
    Args:
        result (dict): 引擎层初步生成的原始风控结果。
        cmd_text (str): 被分析命令原文。
        context (dict): 上下文。
        session_id (str): 指向缓存记录的历史会话标识符。
        current_events (list): 当前请求内分析出的污点行为事件。
    Returns:
        EngineResult: 追加完最终安全状态（标记出风控类型、是否被降级等）并更新库记录后的结果。
    """
    sandbox_downgraded = False
    if (
        context.get("agent_env") == EPHEMERAL_AGENT_ENV
        and result.get("code") == 1
        and result.get("rule_id") in SANDBOX_DOWNGRADE_RULES
        and _can_sandbox_downgrade(cmd_text)
    ):
        result = _result(2, "Review required: downgraded in ephemeral sandbox context.", "REVIEW_SANDBOX_DOWNGRADED")
        sandbox_downgraded = True
    egress_flags: list[str] = []
    if str(result.get("rule_id", "")).startswith("BLOCK_EXFIL") or result.get("rule_id") == "REVIEW_EXFIL_SUSPECTED":
        egress_flags.append("suspected_exfil")
    result = _attach_decision_context(result, context, sandbox_downgraded=sandbox_downgraded, egress_flags=egress_flags)
    EXECUTION_CONTEXT_STORE.append(session_id, current_events)
    return result


def analyze_command_safety(cmd_info: dict[str, Any]) -> EngineResult:
    """ 内部安全分析系统的总控制器：接收统一的数据包裹，分理上下信息，抽取并追踪“连环”漏洞，并顺次触发全局风控检查与专用环境检查引擎。
    Args:
        cmd_info (dict): 从 API 层透传进来的完整请求配置数据。
    Returns:
        EngineResult: 结合各类安全模块深度判定并加工过后的引擎标准结果。
    """
    cmd_text = str(cmd_info.get("command", "")).strip()
    if not cmd_text:
        return _result(0, "Command is empty.", "SAFE_EMPTY_COMMAND")

    cmd_bytes = cmd_text.encode("utf-8", errors="replace")
    if len(cmd_bytes) > MAX_COMMAND_BYTES:
        return _result(2, "Command length exceeded; review required.", "REVIEW_COMMAND_TOO_LONG")

    session_id = str(cmd_info.get("session_id", "default") or "default")
    context = _extract_command_context(cmd_info, cmd_text)
    history = EXECUTION_CONTEXT_STORE.get(session_id)
    current_events = _collect_command_events(cmd_text, context)

    global_risk = _run_global_rules(cmd_text, context)
    if global_risk:
        return _finalize_engine_result(global_risk, cmd_text, context, session_id, current_events)

    taint_chain_risk = _check_taint_execution_chain(cmd_text, context, history, current_events)
    if taint_chain_risk:
        return _finalize_engine_result(taint_chain_risk, cmd_text, context, session_id, current_events)

    shell_type = _resolve_shell_type(cmd_info, cmd_text)
    engine_result = _analyze_by_shell_type(shell_type, cmd_text, cmd_bytes, context)
    return _finalize_engine_result(engine_result, cmd_text, context, session_id, current_events)

# API 接口统一向外部业务返回的状态码常量设定。
SAFE_CODE = 0
REVIEW_CODE = 1
MALICIOUS_CODE = 2

# 引擎内部处理时用来判断威胁阻隔与放宽级别的内置状态码。
INTERNAL_SAFE = 0
INTERNAL_BLOCK = 1
INTERNAL_REVIEW = 2

# 从底层引擎状态转换为外部易懂 API 状态（即内外部业务代码挂靠）。
_SOURCE_TO_TARGET_CODE = {
    INTERNAL_SAFE: SAFE_CODE,
    INTERNAL_BLOCK: MALICIOUS_CODE,
    INTERNAL_REVIEW: REVIEW_CODE,
}

# 格式未校验通过或者缺失必填参数时给外部的默认拒绝拦截模版。
_DEFAULT_INPUT_ERROR = {
    "code": REVIEW_CODE,
    "message": "输入错误：`command` 必须是非空字符串，未执行安全审查。",
}

# 针对各级别告警结果提供的前缀友好文字提示信息。
_PUBLIC_CODE_MESSAGE_PREFIX = {
    SAFE_CODE: "无明显安全风险。",
    REVIEW_CODE: "存在安全风险，需要人工同意。",
    MALICIOUS_CODE: "恶意命令。",
}
# 定义外部传入参数中，哪些可以作为配置字段安全提取进内部环境生效的白名单。
_PUBLIC_CONTEXT_KEYS = (
    "session_id",
    "cwd",
    "workspace_roots",
    "agent_env",
    "trust_profile",
    "shell_type",
    "is_privileged",
)


def _extract_public_command(payload: dict[str, Any]) -> str | None:
    """ 从外部业务下发的 Request Body 当中安全提取需要执行风控探测的 `command` 命令体。
    Args:
        payload (dict): 包含命令的请求体字典。
    Returns:
        str|None: 成功提取则返回去除了空白后的字符串，否则返回 None。
    """
    command = payload.get("command")
    if not isinstance(command, str):
        return None
    normalized = command.strip()
    return normalized or None


def _map_internal_code_to_public(internal_code: int) -> int:
    """ 将内部多级别的阻断评级规范成 0/1/2 这样暴露给 API 的统一安全类别状态码。
    Args:
        internal_code (int): 引擎内部判定的风险数字级别。
    Returns:
        int: 业务线约定的外部响应状态类别值。
    """
    return _SOURCE_TO_TARGET_CODE.get(internal_code, REVIEW_CODE)


def _build_engine_input(command: str, payload: dict[str, Any]) -> dict[str, Any]:
    """ 根据被选中的透传字段白名单提取环境参数，重构拼接为内部引擎可以直接消化的入参格式。
    Args:
        command (str): 被安全扫描引擎执行监测的命令行代码。
        payload (dict): 原始的 API 参数载荷。
    Returns:
        dict[str, Any]: 提炼完毕可供 `analyze_command_safety` 直接调用的干净请求体。
    """
    engine_input: dict[str, Any] = {"command": command}
    for key in _PUBLIC_CONTEXT_KEYS:
        if key not in payload:
            continue
        value = payload.get(key)
        if key == "workspace_roots":
            if isinstance(value, str):
                engine_input[key] = [value]
            elif isinstance(value, list):
                engine_input[key] = [str(item) for item in value]
            continue
        engine_input[key] = value
    return engine_input


def _build_public_message(mapped_code: int, rule_id: str, scanner_message: str) -> str:
    """ 组合从内核出来的风险细则描述与对外约定的安全预警前缀，拼装为对最终用户或者风控审核直观的日志报文。
    Args:
        mapped_code (int): 外部业务的安全威胁状态码。
        rule_id (str): 具体命中的漏洞特征类型 ID。
        scanner_message (str): 引擎内部抛出的具体诊断说明文案。
    Returns:
        str: 连接后的整句完整字符串提示内容。
    """
    prefix = _PUBLIC_CODE_MESSAGE_PREFIX.get(mapped_code, _PUBLIC_CODE_MESSAGE_PREFIX[REVIEW_CODE])
    detail = (scanner_message or "").strip()
    if rule_id:
        return f"{prefix}命中规则：{rule_id}。{detail}" if detail else f"{prefix}命中规则：{rule_id}。"
    return f"{prefix}{detail}" if detail else prefix


def check_bash_command_safety(payload: dict[str, Any]) -> PublicResult:
    """ 【暴露给外部调用的主要 API 函数】
    作为安全评估业务唯一的外部封装大门。接收外部 JSON 形式投递过来的命令行与环境变量配置，将结果包裹翻译为易理解的标准业务响应流。
    Args:
        payload (dict): 前端或者任务系统传达的带执行命令以及其操作目录等配置的字典载体。
    Returns:
        PublicResult: 外部专用的业务反馈结果数据（固定包含 `code` 和 `message`）。
    """
    if not isinstance(payload, dict):
        return dict(_DEFAULT_INPUT_ERROR)

    command = _extract_public_command(payload)
    if not command:
        return dict(_DEFAULT_INPUT_ERROR)

    # 按照外部核心约定提取 `command`，并将其它支持的环境配置通过白名单透传进入内环扫描器。
    scanner_result = analyze_command_safety(_build_engine_input(command, payload))
    source_code = int(scanner_result.get("code", INTERNAL_REVIEW))
    mapped_code = _map_internal_code_to_public(source_code)
    rule_id = str(scanner_result.get("rule_id", "")).strip()
    scanner_message = str(scanner_result.get("message", "")).strip()

    return {
        "code": mapped_code,
        "message": _build_public_message(mapped_code, rule_id, scanner_message),
    }



def main() -> None:
    try:
        if len(sys.argv) < 2:
            raise ValueError("missing payload file path")

        payload_path = sys.argv[1]

        with open(payload_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        result = check_bash_command_safety(payload)

        if not isinstance(result, dict):
            raise ValueError("invalid result type from check_bash_command_safety")

        print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "code": REVIEW_CODE,
            "message": f"audit error: {str(e)}"
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
