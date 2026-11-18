namespace KardeslerVPN;

sealed class MainForm : Form
{
    static readonly Color Green = Color.FromArgb(120, 220, 140);
    static readonly Color Cream = Color.FromArgb(245, 222, 179);
    static readonly Image? Background = LoadImage("bg.jpg");
    readonly Panel card = new() { Width = 420, BackColor = Color.FromArgb(210, 28, 16, 8), Padding = new Padding(20) };

    static Image? LoadImage(string name)
    {
        using var s = typeof(MainForm).Assembly.GetManifestResourceStream(name);
        return s == null ? null : Image.FromStream(new MemoryStream(ReadAll(s)));
    }
    static byte[] ReadAll(Stream s) { using var m = new MemoryStream(); s.CopyTo(m); return m.ToArray(); }

    protected override void OnPaintBackground(PaintEventArgs e)
    {
        if (Background == null) { base.OnPaintBackground(e); return; }
        // "cover": goruntuyu oranini bozmadan pencereyi dolduracak sekilde ortala
        float sc = Math.Max((float)ClientSize.Width / Background.Width, (float)ClientSize.Height / Background.Height);
        int w = (int)(Background.Width * sc), h = (int)(Background.Height * sc);
        e.Graphics.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
        e.Graphics.DrawImage(Background, (ClientSize.Width - w) / 2, (ClientSize.Height - h) / 2, w, h);
    }

    void CenterCard()
    {
        card.Height = Math.Min(ClientSize.Height - 40, 520);
        card.Left = (ClientSize.Width - card.Width) / 2;
        card.Top = (ClientSize.Height - card.Height) / 2;
    }

    readonly Label status = new() { AutoSize = false, Height = 40, Dock = DockStyle.Top, TextAlign = ContentAlignment.MiddleCenter, Font = new Font("Segoe UI", 14f) };
    readonly Button toggle = new() { Height = 56, Dock = DockStyle.Top, Font = new Font("Segoe UI", 14f, FontStyle.Bold), FlatStyle = FlatStyle.Flat, ForeColor = Color.White };
    readonly Panel setup = new() { Dock = DockStyle.Fill, Padding = new Padding(0, 16, 0, 0) };
    readonly TextBox paste = new() { Multiline = true, Dock = DockStyle.Fill, ScrollBars = ScrollBars.Vertical, Font = new Font("Consolas", 10f), PlaceholderText = "[Interface]\r\nPrivateKey = ...\r\n..." };
    readonly LinkLabel reset = new() { Text = "Cihaz kaydını sıfırla", Dock = DockStyle.Bottom, Height = 28, TextAlign = ContentAlignment.MiddleCenter };
    readonly NotifyIcon tray = new() { Text = "Kardeşler VPN" };
    readonly System.Windows.Forms.Timer poll = new() { Interval = 3000 };
    bool busy;

    public MainForm()
    {
        Text = "Kardeşler VPN";
        using (var s = typeof(MainForm).Assembly.GetManifestResourceStream("app.ico"))
            if (s != null) Icon = new Icon(s);
        tray.Icon = Icon;
        ClientSize = new Size(900, 600);
        MinimumSize = new Size(500, 520);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(60, 34, 18);
        ForeColor = Cream;
        DoubleBuffered = true;
        SetStyle(ControlStyles.ResizeRedraw, true);
        Font = new Font("Segoe UI", 10f);

        var title = new Label { Text = "Kardeşler VPN", Dock = DockStyle.Top, Height = 48, TextAlign = ContentAlignment.MiddleCenter, Font = new Font("Segoe UI", 20f, FontStyle.Bold), ForeColor = Cream, BackColor = Color.Transparent };
        toggle.FlatAppearance.BorderSize = 0;
        toggle.Click += async (_, _) => await OnToggle();

        var hint = new Label { BackColor = Color.Transparent, ForeColor = Color.Gainsboro, Dock = DockStyle.Top, Height = 64, Text = "Sunucuda  sudo bash wg-kur.sh ekle <isim>  komutunun yazdığı ayarı aşağıya yapıştırın ya da .conf dosyasını açın." };
        var buttons = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 44, FlowDirection = FlowDirection.RightToLeft, Padding = new Padding(0, 6, 0, 0) };
        var save = new Button { Text = "Ayarı kaydet", AutoSize = true, Height = 32 };
        var open = new Button { Text = "Dosyadan aç...", AutoSize = true, Height = 32 };
        save.Click += (_, _) => SaveConfig(paste.Text);
        open.Click += (_, _) => OpenFile();
        buttons.Controls.Add(save); buttons.Controls.Add(open);
        setup.Controls.Add(paste); setup.Controls.Add(hint); setup.Controls.Add(buttons);

        reset.LinkClicked += async (_, _) => await Reset();

        status.BackColor = Color.Transparent;
        setup.BackColor = Color.Transparent;
        buttons.BackColor = Color.Transparent;
        reset.BackColor = Color.Transparent;
        reset.LinkColor = Cream; reset.ActiveLinkColor = Color.White;
        foreach (var b in new[] { save, open }) { b.BackColor = Color.FromArgb(245, 236, 220); b.ForeColor = Color.Black; }
        card.Controls.Add(setup);
        card.Controls.Add(reset);
        card.Controls.Add(toggle);
        card.Controls.Add(status);
        card.Controls.Add(title);
        Controls.Add(card);
        Resize += (_, _) => CenterCard();
        CenterCard();

        tray.DoubleClick += (_, _) => { Show(); WindowState = FormWindowState.Normal; Activate(); };
        tray.ContextMenuStrip = new ContextMenuStrip();
        tray.ContextMenuStrip.Items.Add("Aç", null, (_, _) => { Show(); WindowState = FormWindowState.Normal; });
        tray.ContextMenuStrip.Items.Add("Çıkış", null, (_, _) => { tray.Visible = false; Application.Exit(); });
        Resize += (_, _) => { if (WindowState == FormWindowState.Minimized) { Hide(); tray.Visible = true; } };
        FormClosed += (_, _) => tray.Visible = false;

        poll.Tick += (_, _) => { if (!busy) Refresh2(); };
        poll.Start();
        Refresh2();
    }

    void Refresh2(string? message = null)
    {
        bool hasCfg = Tunnel.HasConfig, up = hasCfg && Tunnel.IsUp;
        status.Text = message ?? (!hasCfg ? "Cihaz kayıtlı değil" : up ? "Bağlı ✓" : "Bağlı değil");
        status.ForeColor = up ? Green : Color.Gainsboro;
        toggle.Text = up ? "Bağlantıyı kes" : "Bağlan";
        toggle.BackColor = !hasCfg ? Color.DimGray : up ? Color.Firebrick : Color.FromArgb(176, 28, 36);
        toggle.Enabled = hasCfg && !busy;
        setup.Visible = !hasCfg;
        reset.Visible = hasCfg;
        tray.Text = up ? "Kardeşler VPN: bağlı" : "Kardeşler VPN";
    }

    async Task OnToggle()
    {
        busy = true; toggle.Enabled = false;
        bool up = Tunnel.IsUp;
        try
        {
            if (!up && !Tunnel.ComponentInstalled)
                await Tunnel.InstallComponent(new Progress<string>(m => status.Text = m));
            status.Text = up ? "Kesiliyor..." : "Bağlanıyor...";
            if (up) await Tunnel.Down(); else await Tunnel.Up();
            busy = false; Refresh2();
        }
        catch (Exception e)
        {
            busy = false; Refresh2("Hata: " + e.Message);
        }
    }

    void SaveConfig(string text)
    {
        var err = Tunnel.Validate(text);
        if (err != null) { Refresh2("Ayar geçersiz: " + err); return; }
        try { Tunnel.SaveConfig(text); paste.Clear(); Refresh2(); }
        catch (Exception e) { Refresh2("Kaydedilemedi: " + e.Message); }
    }

    void OpenFile()
    {
        using var dlg = new OpenFileDialog { Filter = "WireGuard ayarı (*.conf)|*.conf|Tüm dosyalar|*.*" };
        if (dlg.ShowDialog(this) == DialogResult.OK) SaveConfig(File.ReadAllText(dlg.FileName));
    }

    async Task Reset()
    {
        if (MessageBox.Show(this, "Bu bilgisayarın VPN ayarı silinsin mi?", "Kardeşler VPN", MessageBoxButtons.YesNo) != DialogResult.Yes) return;
        busy = true;
        try { if (Tunnel.IsUp) await Tunnel.Down(); Tunnel.DeleteConfig(); }
        catch (Exception e) { busy = false; Refresh2("Hata: " + e.Message); return; }
        busy = false; Refresh2();
    }
}
