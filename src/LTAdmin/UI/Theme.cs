using System.Drawing.Drawing2D;

namespace LTAdmin.UI;

internal static class Theme
{
    public static readonly Color Background = Color.FromArgb(245, 247, 250);
    public static readonly Color Surface = Color.White;
    public static readonly Color Sidebar = Color.FromArgb(19, 31, 52);
    public static readonly Color SidebarMuted = Color.FromArgb(148, 163, 184);
    public static readonly Color Primary = Color.FromArgb(30, 105, 217);
    public static readonly Color PrimaryDark = Color.FromArgb(20, 78, 160);
    public static readonly Color Text = Color.FromArgb(30, 41, 59);
    public static readonly Color MutedText = Color.FromArgb(100, 116, 139);
    public static readonly Color Border = Color.FromArgb(226, 232, 240);
    public static readonly Color Success = Color.FromArgb(15, 138, 96);
    public static readonly Color Warning = Color.FromArgb(205, 126, 22);
    public static readonly Font Body = new("Segoe UI", 9.5f, FontStyle.Regular);
    public static readonly Font BodyBold = new("Segoe UI", 9.5f, FontStyle.Bold);
    public static readonly Font Small = new("Segoe UI", 8.5f, FontStyle.Regular);
    public static readonly Font Heading = new("Segoe UI Semibold", 20f, FontStyle.Bold);
    public static readonly Font SubHeading = new("Segoe UI Semibold", 12f, FontStyle.Bold);

    public static Button Button(string text, Color backColor, Color foreColor, int width = 110)
    {
        var button = new Button
        {
            Text = text,
            Width = width,
            Height = 34,
            FlatStyle = FlatStyle.Flat,
            BackColor = backColor,
            ForeColor = foreColor,
            Font = BodyBold,
            Cursor = Cursors.Hand,
            FlatAppearance = { BorderSize = 0 }
        };
        return button;
    }

    public static Panel Card(int radius = 10)
    {
        var panel = new Panel { BackColor = Surface, Padding = new Padding(18) };
        panel.Paint += (_, e) =>
        {
            using var pen = new Pen(Border);
            using var path = RoundedPath(panel.ClientRectangle, radius);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.DrawPath(pen, path);
        };
        return panel;
    }

    public static GraphicsPath RoundedPath(Rectangle rectangle, int radius)
    {
        var path = new GraphicsPath();
        var diameter = radius * 2;
        var bounds = new Rectangle(rectangle.X, rectangle.Y, Math.Max(0, rectangle.Width - 1), Math.Max(0, rectangle.Height - 1));
        path.AddArc(bounds.X, bounds.Y, diameter, diameter, 180, 90);
        path.AddArc(bounds.Right - diameter, bounds.Y, diameter, diameter, 270, 90);
        path.AddArc(bounds.Right - diameter, bounds.Bottom - diameter, diameter, diameter, 0, 90);
        path.AddArc(bounds.X, bounds.Bottom - diameter, diameter, diameter, 90, 90);
        path.CloseFigure();
        return path;
    }

    public static void StyleGrid(DataGridView grid)
    {
        grid.BackgroundColor = Surface;
        grid.BorderStyle = BorderStyle.None;
        grid.CellBorderStyle = DataGridViewCellBorderStyle.SingleHorizontal;
        grid.GridColor = Border;
        grid.RowHeadersVisible = false;
        grid.AllowUserToAddRows = false;
        grid.AllowUserToDeleteRows = false;
        grid.AllowUserToResizeRows = false;
        grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        grid.MultiSelect = false;
        grid.ReadOnly = true;
        grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
        grid.AutoSizeRowsMode = DataGridViewAutoSizeRowsMode.None;
        grid.RowTemplate.Height = 34;
        grid.ColumnHeadersHeight = 38;
        grid.EnableHeadersVisualStyles = false;
        grid.ColumnHeadersDefaultCellStyle = new DataGridViewCellStyle
        {
            BackColor = Color.FromArgb(241, 245, 249), ForeColor = Text, Font = BodyBold,
            SelectionBackColor = Color.FromArgb(241, 245, 249), SelectionForeColor = Text,
            Padding = new Padding(8, 0, 8, 0)
        };
        grid.DefaultCellStyle = new DataGridViewCellStyle
        {
            BackColor = Surface, ForeColor = Text, Font = Body,
            SelectionBackColor = Color.FromArgb(224, 236, 252), SelectionForeColor = Text,
            Padding = new Padding(8, 0, 8, 0
            )
        };
    }
}
