package com.cz.familycut.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.cz.familycut.data.model.ThemeMode
import com.cz.familycut.ui.components.AppPageColumn
import com.cz.familycut.ui.components.GlassFilterChip
import com.cz.familycut.ui.components.GlassPrimaryButton
import com.cz.familycut.ui.components.GlassSecondaryButton
import com.cz.familycut.ui.components.GlassTextField
import com.cz.familycut.ui.components.HeroCard
import com.cz.familycut.ui.components.HeroPillRow
import com.cz.familycut.ui.components.SectionCard

@Composable
fun SettingsScreen(
    innerPadding: PaddingValues,
    selectedThemeMode: ThemeMode,
    serverUrl: String,
    onSelectTheme: (ThemeMode) -> Unit,
    onSaveServerUrl: (String) -> Unit,
    onLogout: () -> Unit
) {
    var serverUrlInput by remember(serverUrl) { mutableStateOf(serverUrl) }

    AppPageColumn(innerPadding = innerPadding) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            HeroCard(
                title = "显示与连接设置",
                subtitle = "这里管理主题和服务器地址。默认已经是 Lucky 的 HTTPS 地址，必要时你也可以切回内网地址。"
            )
            HeroPillRow(
                if (selectedThemeMode == ThemeMode.FOLLOW_SYSTEM) "主题 跟随系统" else "主题 ${if (selectedThemeMode == ThemeMode.LIGHT) "浅色" else "深色"}",
                "连接已保存",
                "账号可随时退出"
            )
        }

        SectionCard(title = "服务器", subtitle = "优先保持外网 Lucky 地址稳定，仅在排障时临时切回内网。") {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                GlassTextField(
                    value = serverUrlInput,
                    onValueChange = { serverUrlInput = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "服务器 API 地址"
                )
                GlassPrimaryButton(
                    text = "保存服务器地址",
                    onClick = { onSaveServerUrl(serverUrlInput) },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        SectionCard(title = "主题", subtitle = "当前先提供跟随系统、浅色、深色三种模式。") {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                listOf(
                    ThemeMode.FOLLOW_SYSTEM to "跟随系统",
                    ThemeMode.LIGHT to "浅色模式",
                    ThemeMode.DARK to "深色模式"
                ).forEach { (mode, label) ->
                    GlassFilterChip(label = label, selected = selectedThemeMode == mode, onClick = { onSelectTheme(mode) })
                }
            }
        }

        GlassSecondaryButton(text = "退出登录", onClick = onLogout, modifier = Modifier.fillMaxWidth())
    }
}
