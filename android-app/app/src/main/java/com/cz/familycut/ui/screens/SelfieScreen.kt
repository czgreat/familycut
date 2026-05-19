package com.cz.familycut.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.cz.familycut.data.remote.MediaAssetResponse
import com.cz.familycut.ui.components.AppPage
import com.cz.familycut.ui.components.GlassPrimaryButton
import com.cz.familycut.ui.components.GlassSecondaryButton
import com.cz.familycut.ui.components.GlassTextField
import com.cz.familycut.ui.components.HeroCard
import com.cz.familycut.ui.components.HeroPillRow
import com.cz.familycut.ui.components.InlineCameraCapture
import com.cz.familycut.ui.components.SectionCard
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun SelfieScreen(
    innerPadding: PaddingValues,
    serverUrl: String,
    selfieBusy: Boolean,
    lastSelfieUploadAt: Long?,
    selfieNote: String,
    recentSelfies: List<MediaAssetResponse>,
    onNoteChange: (String) -> Unit,
    onUpload: (ByteArray, String, String?) -> Unit
) {
    val context = LocalContext.current
    var selectedPreviewUri by remember { mutableStateOf<Uri?>(null) }
    var selectedBytes by remember { mutableStateOf<ByteArray?>(null) }
    var selectedName by remember { mutableStateOf("selfie.jpg") }
    var selectedMimeType by remember { mutableStateOf<String?>(null) }
    var cameraOpen by remember { mutableStateOf(false) }

    val pickerLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            selectedPreviewUri = uri
            selectedBytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
            selectedMimeType = context.contentResolver.getType(uri)
            selectedName = guessFileName(uri)
        }
    }

    LaunchedEffect(lastSelfieUploadAt) {
        if (lastSelfieUploadAt != null) {
            selectedPreviewUri = null
            selectedBytes = null
            selectedName = "selfie.jpg"
            selectedMimeType = null
        }
    }

    AppPage(innerPadding = innerPadding) {
        LazyColumn(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    HeroCard(
                        title = "自拍记录",
                        subtitle = "自拍默认前置相机，仅保留私有记录上传和时间轴浏览。"
                    )
                    HeroPillRow(
                        "前置自拍",
                        if (recentSelfies.isEmpty()) "最近无记录" else "最近 ${recentSelfies.size} 条",
                        if (selfieBusy) "上传中" else "私有时间轴"
                    )
                }
            }

            item {
                SectionCard(title = "上传今天的自拍", subtitle = "自拍拍摄默认启用前置镜头，先看预览再上传。") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        if (cameraOpen) {
                            InlineCameraCapture(
                                lensFacing = CameraSelector.LENS_FACING_FRONT,
                                label = "前置相机",
                                onCapture = { bytes, fileName, mimeType ->
                                    selectedBytes = bytes
                                    selectedName = fileName
                                    selectedMimeType = mimeType
                                    selectedPreviewUri = null
                                    cameraOpen = false
                                },
                                onClose = { cameraOpen = false }
                            )
                        } else {
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                GlassPrimaryButton(text = "前置自拍", onClick = { cameraOpen = true }, modifier = Modifier.weight(1f))
                                GlassSecondaryButton(text = "相册导入", onClick = { pickerLauncher.launch("image/*") }, modifier = Modifier.weight(1f))
                            }
                        }

                        if (selectedPreviewUri != null) {
                            AsyncImage(
                                model = selectedPreviewUri,
                                contentDescription = "自拍预览",
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                        if (selectedBytes != null) {
                            Text(
                                text = "拍照完成后，请检查备注，再点下方上传。",
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                        GlassTextField(
                            value = selfieNote,
                            onValueChange = onNoteChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = "备注（可选）"
                        )
                        GlassPrimaryButton(
                            text = if (selfieBusy) "正在上传..." else "上传自拍",
                            onClick = {
                                val bytes = selectedBytes
                                if (bytes != null) {
                                    onUpload(bytes, selectedName, selectedMimeType)
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            enabled = selectedBytes != null && !selfieBusy
                        )
                    }
                }
            }

            item {
                SectionCard(title = "最近自拍", subtitle = "当前只展示私有自拍时间轴，保证回看时更专注。") {
                    if (recentSelfies.isEmpty()) {
                        Text("还没有自拍记录。")
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                            recentSelfies.take(10).forEach { asset ->
                                val imageUrl = resolveMediaUrl(serverUrl, asset.previewUrl ?: asset.originalUrl)
                                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    if (imageUrl != null) {
                                        AsyncImage(
                                            model = imageUrl,
                                            contentDescription = "自拍时间轴图片",
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                    }
                                    Text(formatCapturedTime(asset.capturedAt), style = MaterialTheme.typography.titleMedium)
                                    if (!asset.note.isNullOrBlank()) {
                                        Text(asset.note, style = MaterialTheme.typography.bodyMedium)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun guessFileName(uri: Uri): String {
    val lastSegment = uri.lastPathSegment?.substringAfterLast('/')
    return when {
        !lastSegment.isNullOrBlank() -> lastSegment
        else -> "selfie-${System.currentTimeMillis()}.jpg"
    }
}

private fun resolveMediaUrl(serverUrl: String, path: String?): String? {
    if (path.isNullOrBlank()) return null
    if (path.startsWith("http://") || path.startsWith("https://")) return path
    val origin = serverUrl.substringBefore("/api/")
    return "$origin$path"
}

private fun formatCapturedTime(raw: String): String {
    return runCatching {
        Instant.parse(raw)
            .atZone(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern("M月d日 HH:mm"))
    }.getOrDefault(raw)
}
