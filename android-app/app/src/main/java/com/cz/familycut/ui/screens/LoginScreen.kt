package com.cz.familycut.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.cz.familycut.ui.components.AppPageColumn
import com.cz.familycut.ui.components.GlassPrimaryButton
import com.cz.familycut.ui.components.GlassSecondaryButton
import com.cz.familycut.ui.components.GlassTextField
import com.cz.familycut.ui.components.HeroCard
import com.cz.familycut.ui.components.HeroPillRow
import com.cz.familycut.ui.components.SectionCard

@Composable
fun LoginScreen(
    loginBusy: Boolean,
    serverUrl: String,
    onLogin: (String, String, String) -> Unit,
    onOpenInviteJoin: () -> Unit
) {
    var serverUrlInput by remember(serverUrl) { mutableStateOf(serverUrl) }
    var username by remember { mutableStateOf("admin") }
    var password by remember { mutableStateOf("1099040334") }

    AppPageColumn {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            HeroCard(
                title = "FamilyCut",
                subtitle = "管理员可以直接登录后台，其它家庭成员通过邀请码加入。默认服务器地址已经指向 Lucky HTTPS 入口。"
            )
            HeroPillRow(
                "默认 HTTPS 入口",
                "管理员直登",
                "邀请码加入"
            )
        }

        SectionCard(title = "管理员登录", subtitle = "输入账号后直接进入应用主页，不再依赖系统返回键来找入口。") {
            androidx.compose.foundation.layout.Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                GlassTextField(
                    value = serverUrlInput,
                    onValueChange = { serverUrlInput = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "服务器 API 地址"
                )
                GlassTextField(
                    value = username,
                    onValueChange = { username = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "账号"
                )
                GlassTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "密码"
                )
                GlassPrimaryButton(
                    text = if (loginBusy) "正在登录..." else "管理员登录",
                    onClick = { onLogin(serverUrlInput, username, password) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !loginBusy
                )
                GlassSecondaryButton(
                    text = "邀请码加入家庭",
                    onClick = onOpenInviteJoin,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !loginBusy
                )
            }
        }

        SectionCard(title = "默认信息", subtitle = "当前安装包保留默认管理员账号提示，方便首次进入。") {
            Text(
                text = "默认管理员账号：admin",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
        }
    }
}
