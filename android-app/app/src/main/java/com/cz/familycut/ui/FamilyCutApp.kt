package com.cz.familycut.ui

import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import com.cz.familycut.ui.navigation.AppNavGraph
import com.cz.familycut.ui.theme.FamilyCutTheme
import com.cz.familycut.ui.viewmodel.MainViewModel

@Composable
fun FamilyCutApp(viewModel: MainViewModel) {
    val themeMode by viewModel.themeMode.collectAsState()
    val session by viewModel.session.collectAsState()
    val notice by viewModel.notice.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(notice) {
        notice?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.consumeNotice()
        }
    }

    FamilyCutTheme(themeMode = themeMode) {
        AppNavGraph(
            session = session,
            viewModel = viewModel,
            snackbarHostState = snackbarHostState
        )
    }
}
