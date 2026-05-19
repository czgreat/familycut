# 架构速记

## 后端

- `FastAPI`
- `SQLAlchemy + PostgreSQL`
- `Redis + worker`
- `Caddy`

主链路：

1. App 登录或加入家庭
2. 体重、餐次、自拍上传到后端
3. 营养表图片经 `NewAPI` 解析成草稿
4. App 人工修正后提交正式饮食记录
5. 服务端按成员生成日报并推送可选通知

## Android

- `Kotlin + Compose`
- `Room` 作为本地缓存和离线队列
- `DataStore` 保存主题模式
- `WorkManager` 预留给后台同步

## 用户端 PWA

- `React + Vite + TypeScript`
- `react-router`
- `@tanstack/react-query`
- `vite-plugin-pwa`
- 轻离线缓存当前覆盖静态资源、首页摘要、表单草稿和识别中的本地状态
- 部署形态当前规划为同域子路径 `/m/`

## 管理后台

- `React + Vite`
- 配置 AI provider、成员和通知策略
- 查看汇总、历史日报和共享媒体
