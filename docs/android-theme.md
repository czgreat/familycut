# Android 深色 / 浅色模式

Android 客户端默认支持三种主题策略：

- `Follow system`: 跟随系统深浅色
- `Light`: 强制浅色
- `Dark`: 强制深色

## 当前实现

- 枚举定义在 `ThemeMode.kt`
- 偏好通过 `DataStore` 持久化
- `FamilyCutTheme` 根据 `ThemeMode` 决定浅色或深色 `Material 3 colorScheme`
- 设置页可直接切换主题，重启后仍保持原值

## 设计边界

- 首版不启用 Material You 动态色，先保证色板稳定和截图一致性
- 导出的日报长图不跟随 App 当前主题，后续应使用固定模板色板
- 若系统切换深浅色而用户仍处于 `Follow system`，Compose 会自动重组刷新 UI
