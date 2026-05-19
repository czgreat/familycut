package com.cz.familycut.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
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
import com.cz.familycut.ui.components.GlassFilterChip
import com.cz.familycut.ui.components.GlassPrimaryButton
import com.cz.familycut.ui.components.GlassTextField
import com.cz.familycut.ui.components.HeroCard
import com.cz.familycut.ui.components.HeroPillRow
import com.cz.familycut.ui.components.SectionCard

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun InviteJoinScreen(
    innerPadding: PaddingValues,
    busy: Boolean,
    serverUrl: String,
    invitePreview: String,
    onPreviewInvite: (String, String) -> Unit,
    onJoin: (String, String, String, String, String, String, String) -> Unit
) {
    var serverUrlInput by remember(serverUrl) { mutableStateOf(serverUrl) }
    var inviteCode by remember { mutableStateOf("") }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var displayName by remember { mutableStateOf("") }
    var sex by remember { mutableStateOf("") }
    var birthYear by remember { mutableStateOf("") }

    AppPageColumn(innerPadding = innerPadding) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            HeroCard(
                title = "邀请码加入",
                subtitle = "管理员先在后台生成邀请码，成员再用邀请码建立自己的账号并加入家庭。首次注册要填性别和出生年份，后面才能算年龄和 TDEE。"
            )
            HeroPillRow(
                "先检查邀请码",
                "再创建账号",
                "最后补资料"
            )
        }

        SectionCard(title = "邀请码验证", subtitle = "先检查邀请码是否有效，再填写成员信息。") {
            androidx.compose.foundation.layout.Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                GlassTextField(
                    value = serverUrlInput,
                    onValueChange = { serverUrlInput = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "服务器 API 地址"
                )
                GlassTextField(
                    value = inviteCode,
                    onValueChange = { inviteCode = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "邀请码"
                )
                GlassPrimaryButton(
                    text = "检查邀请码",
                    onClick = { onPreviewInvite(serverUrlInput, inviteCode) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !busy
                )
                if (invitePreview.isNotBlank()) {
                    Text(
                        text = invitePreview,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }

        SectionCard(title = "创建成员账号") {
            androidx.compose.foundation.layout.Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                GlassTextField(
                    value = displayName,
                    onValueChange = { displayName = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "显示名"
                )
                GlassTextField(
                    value = username,
                    onValueChange = { username = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "账号"
                )
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("male" to "男", "female" to "女").forEach { (value, label) ->
                        GlassFilterChip(label = label, selected = sex == value, onClick = { sex = value })
                    }
                }
                GlassTextField(
                    value = birthYear,
                    onValueChange = { birthYear = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "出生年份（用于年龄 / TDEE）"
                )
                GlassTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "密码"
                )
                GlassPrimaryButton(
                    text = if (busy) "正在加入..." else "加入家庭",
                    onClick = { onJoin(serverUrlInput, inviteCode, username, password, displayName, sex, birthYear) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !busy
                )
            }
        }
    }
}
