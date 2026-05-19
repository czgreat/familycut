# 使用和 API 示例

**语言：** [English](USAGE_EXAMPLES.md) | 中文

这些示例使用公开安全的占位数据。复制到自己的环境前，请替换 URL、token、路径和配置，并确认你有权处理对应数据。

## 示例 1：后端健康检查

启动 compose 栈后先验证后端，再打开 Web 应用。

## 示例 2：本地 Web 开发

开发 UI 时可分别运行管理端和移动端 Web，并连接本地后端。

## curl 示例

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/docs
```

接口请求体会随版本变化；以本地 `/docs` 或源码里的模型定义为准。


## 本地验证建议

- 先按 `README.zh-CN.md` 启动项目。
- 先调用健康检查，再执行会写入状态或发通知的操作。
- 使用合成数据或公开演示数据，不要把私人数据写进 issue、截图或提交。
- 如果让 AI assistant 帮忙，把本文件、部署文档和已去敏日志一起提供给它。
