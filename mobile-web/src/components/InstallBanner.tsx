import { useInstallPrompt } from "../lib/install";

export function InstallBanner() {
  const install = useInstallPrompt();

  if (!install.shouldShowBanner) {
    return null;
  }

  return (
    <section className="install-banner">
      <div>
        <p className="install-banner-kicker">Install</p>
        <strong>把 FamilyCut 放到主屏幕</strong>
        {install.iosSafari ? (
          <p>iPhone 上不会弹系统安装框。请点浏览器分享按钮，再选“添加到主屏幕”。</p>
        ) : (
          <p>可以直接安装到主屏幕，像应用一样打开。</p>
        )}
      </div>
      <div className="install-banner-actions">
        {install.canPromptInstall ? (
          <button className="secondary-button" type="button" onClick={() => void install.promptInstall()}>
            安装
          </button>
        ) : null}
        <button className="install-banner-dismiss" type="button" onClick={install.dismiss}>
          知道了
        </button>
      </div>
    </section>
  );
}
