# 开发机启动时挂载只读目录到工作目录

## Context

当前开发机的只读存储（`Storage.ReadOnly=true`）通过 Kubernetes VolumeMount 挂载到容器的 `MountPath`，但用户希望这些只读目录的内容在工作目录下可见。方案是将只读目录信息通过环境变量传递给容器，由 bootstrap 脚本从 env 读取并处理挂载到工作目录的逻辑。

## 实现方案

### 后端职责：将只读 Storage 的挂载路径写入 env

**文件**: `internal/service/devmachine/resource_builder.go`

从 `request.Storage` 中筛选 `ReadOnly=true` 的项，将它们的 `MountPath` 拼接为环境变量传递给容器。

#### 1. 新增辅助函数：构建只读挂载路径 env

```go
// buildReadonlyMountPathsEnv 从 storage 列表中提取只读挂载路径，逗号分隔
func buildReadonlyMountPathsEnv(storages []devmachinemodel.Storage) string {
    var paths []string
    for _, s := range storages {
        if s.ReadOnly {
            paths = append(paths, s.MountPath)
        }
    }
    return strings.Join(paths, ",")
}
```

#### 2. 修改 `buildJupyterEnv()` 和 `buildVSCodeEnv()`

两个函数增加 `storages []devmachinemodel.Storage` 参数，在返回的 env 列表中追加：

```go
{
    Name:  "RO_MOUNT_PATHS",
    Value: buildReadonlyMountPathsEnv(storages),
}
```

只在有只读目录时才添加此 env。

#### 3. 更新调用方

- `buildJupyterContainer()` (line 196): `buildJupyterEnv(request.WorkDir)` → `buildJupyterEnv(request.WorkDir, request.Storage)`
- `buildVSCodeContainer()` (line 280): `buildVSCodeEnv(request.WorkDir)` → `buildVSCodeEnv(request.WorkDir, request.Storage)`

### Env 格式

- **Key**: `RO_MOUNT_PATHS`
- **Value**: 逗号分隔的只读挂载路径，如 `/data/datasets,/data/models`
- bootstrap 脚本读取此 env，将每个路径挂载（拷贝/软链接）到 `WORKDIR` 对应目录下

### 不需要改动的部分

- VolumeMount / Volume 构建逻辑不变
- 启动命令 `buildUserContainerCommand()` 不变
- 数据模型不变
- 状态机不变

## 关键文件

- `internal/service/devmachine/resource_builder.go` — 唯一需要修改的文件

## 验证方式

1. 创建带只读 Storage 的开发机，检查 Pod spec 中容器 env 包含 `RO_MOUNT_PATHS`
2. 检查无只读 Storage 时不添加该 env
3. 验证多个只读目录时逗号分隔格式正确
