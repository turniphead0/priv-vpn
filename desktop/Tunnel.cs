using System.Diagnostics;
using System.Security.AccessControl;
using System.Security.Principal;
using System.ServiceProcess;

namespace KardeslerVPN;

/// <summary>
/// Resmi WireGuard for Windows bileseninin tunel servisini yonetir.
/// Tunel "WireGuardTunnel$kardesler" adli bir Windows servisi olarak calisir;
/// uygulama kapansa da bilgisayar yeniden baslasa da baglanti korunur.
/// </summary>
static class Tunnel
{
    public const string Name = "kardesler";
    const string MsiUrl = "https://download.wireguard.com/windows-client/wireguard-amd64-0.5.3.msi";

    static readonly string DataDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "KardeslerVPN");
    public static string ConfigPath => Path.Combine(DataDir, Name + ".conf");

    static string WireGuardExe => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "WireGuard", "wireguard.exe");

    public static bool ComponentInstalled => File.Exists(WireGuardExe);
    public static bool HasConfig => File.Exists(ConfigPath);

    public static bool IsUp
    {
        get
        {
            try
            {
                using var sc = new ServiceController("WireGuardTunnel$" + Name);
                return sc.Status is ServiceControllerStatus.Running or ServiceControllerStatus.StartPending;
            }
            catch (InvalidOperationException) { return false; }
        }
    }

    public static string? Validate(string text)
    {
        if (!text.Contains("[Interface]")) return "[Interface] bölümü yok.";
        if (!text.Contains("PrivateKey")) return "PrivateKey satırı yok.";
        if (!text.Contains("[Peer]")) return "[Peer] bölümü yok.";
        if (!text.Contains("Endpoint")) return "Endpoint satırı yok.";
        return null;
    }

    public static void SaveConfig(string text)
    {
        // Sadece SYSTEM ve Yoneticiler okuyabilsin: dosyada gizli anahtar var.
        var sec = new DirectorySecurity();
        sec.SetAccessRuleProtection(true, false);
        foreach (var sid in new[] { WellKnownSidType.LocalSystemSid, WellKnownSidType.BuiltinAdministratorsSid })
            sec.AddAccessRule(new FileSystemAccessRule(new SecurityIdentifier(sid, null), FileSystemRights.FullControl,
                InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
        var dir = new DirectoryInfo(DataDir);
        if (!dir.Exists) dir.Create(sec); else dir.SetAccessControl(sec);
        File.WriteAllText(ConfigPath, text.Replace("\r\n", "\n").Trim() + "\n");
    }

    public static void DeleteConfig()
    {
        if (File.Exists(ConfigPath)) File.Delete(ConfigPath);
    }

    public static async Task Up()
    {
        if (IsUp) await Down();
        await Run(WireGuardExe, $"/installtunnelservice \"{ConfigPath}\"");
        for (int i = 0; i < 20 && !IsUp; i++) await Task.Delay(500);
        if (!IsUp) throw new Exception("Tünel servisi başlamadı.");
    }

    public static async Task Down()
    {
        await Run(WireGuardExe, $"/uninstalltunnelservice {Name}");
        for (int i = 0; i < 20 && IsUp; i++) await Task.Delay(500);
    }

    public static async Task InstallComponent(IProgress<string> progress)
    {
        var msi = Path.Combine(Path.GetTempPath(), "wireguard-amd64.msi");
        progress.Report("WireGuard bileşeni indiriliyor...");
        using (var http = new HttpClient())
        await using (var fs = File.Create(msi))
            await (await http.GetStreamAsync(MsiUrl)).CopyToAsync(fs);
        progress.Report("WireGuard bileşeni kuruluyor...");
        await Run("msiexec.exe", $"/i \"{msi}\" /qn /norestart DO_NOT_LAUNCH=1");
        File.Delete(msi);
        if (!ComponentInstalled) throw new Exception("Kurulum tamamlanamadı.");
    }

    static async Task Run(string exe, string args)
    {
        var psi = new ProcessStartInfo(exe, args)
        {
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardError = true, RedirectStandardOutput = true,
        };
        using var p = Process.Start(psi) ?? throw new Exception(exe + " başlatılamadı.");
        var err = await p.StandardError.ReadToEndAsync();
        await p.WaitForExitAsync();
        if (p.ExitCode != 0)
            throw new Exception($"{Path.GetFileName(exe)} hata kodu {p.ExitCode}. {err}".Trim());
    }
}
