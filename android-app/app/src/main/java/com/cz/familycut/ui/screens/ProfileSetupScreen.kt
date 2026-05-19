package com.cz.familycut.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.cz.familycut.data.model.UserSession
import com.cz.familycut.ui.components.AppPageColumn
import com.cz.familycut.ui.components.GlassFilterChip
import com.cz.familycut.ui.components.GlassPrimaryButton
import com.cz.familycut.ui.components.GlassTextField
import com.cz.familycut.ui.components.HeroCard
import com.cz.familycut.ui.components.HeroPillRow
import com.cz.familycut.ui.components.SectionCard

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ProfileSetupScreen(
    innerPadding: PaddingValues,
    session: UserSession?,
    busy: Boolean,
    onSave: (String, String, String, String) -> Unit
) {
    var displayName by remember(session?.displayName) { mutableStateOf(session?.displayName ?: "") }
    var sex by remember(session?.sex) { mutableStateOf(session?.sex ?: "") }
    var birthYear by remember(session?.birthYear) { mutableStateOf(session?.birthYear?.toString() ?: "") }
    var heightCm by remember(session?.heightCm) { mutableStateOf(session?.heightCm?.toString() ?: "") }

    AppPageColumn(innerPadding = innerPadding) {
            HeroCard(
                title = "完善资料",
                subtitle = "先补齐基础信息，之后每次新体重都会带着 BMR、TDEE 和每日宏量目标一起更新。"
            )
        HeroPillRow(
            if (session?.displayName.isNullOrBlank()) "首次补资料" else "正在编辑资料",
            if (session?.birthYear != null) "生日已锁定" else "生日待填写",
            if (session?.sex != null) "性别已锁定" else "性别待填写"
        )

        SectionCard(title = "基础信息", subtitle = "先固定不会频繁变化的身体参数，再回到首页继续记录。") {
            androidx.compose.foundation.layout.Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                GlassTextField(
                    value = displayName,
                    onValueChange = { displayName = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "显示名"
                )
                if (session?.sex != null) {
                    Text("性别：${if (session.sex == "male") "男" else "女"}（首次设置后不可修改）", style = MaterialTheme.typography.bodyMedium)
                } else {
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("male" to "男", "female" to "女").forEach { (value, label) ->
                            GlassFilterChip(label = label, selected = sex == value, onClick = { sex = value })
                        }
                    }
                }
                if (session?.birthYear != null) {
                    Text("出生年份：${session.birthYear}（首次设置后不可修改）", style = MaterialTheme.typography.bodyMedium)
                } else {
                    GlassTextField(
                        value = birthYear,
                        onValueChange = { birthYear = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = "出生年份（用于年龄 / TDEE）"
                    )
                }
                GlassTextField(
                    value = heightCm,
                    onValueChange = { heightCm = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = "身高（cm）"
                )
                GlassPrimaryButton(
                    text = if (busy) "正在保存..." else "保存资料",
                    onClick = { onSave(displayName, sex, birthYear, heightCm) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !busy
                )
            }
        }
    }
}
