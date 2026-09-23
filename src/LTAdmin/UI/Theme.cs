using System.Drawing.Drawing2D;

namespace LTAdmin.UI;

internal static class Theme
{
    // Dark theme palette
    public static readonly Color Background = Color.FromArgb(30, 30, 30);
    public static readonly Color Surface = Color.FromArgb(45, 45, 48);
    public static readonly Color Sidebar = Color.FromArgb(19, 31, 52);
    public static readonly Color SidebarMuted = Color.FromArgb(80, 100, 120);
    public static readonly Color Primary = Color.FromArgb(0, 191, 165); // teal accent
    public static readonly Color PrimaryDark = Color.FromArgb(0, 150, 130);
    public static readonly Color Text = Color.FromArgb(230, 230, 230);
    public static readonly Color MutedText = Color.FromArgb(150, 150, 150);
    public static readonly Color Border = Color.FromArgb(60, 70, 80);
    public static readonly Color Success = Color.FromArgb(15, 138, 96);
    public static readonly Color Warning = Color.FromArgb(205, 126, 22);
    // Inter font family (Google Font)
    public static readonly Font Body = new("Inter", 9.5f, FontStyle.Regular);
    public static readonly Font BodyBold = new("Inter", 9.5f, FontStyle.Bold);
    public static readonly Font Small = new("Inter", 8.5f, FontStyle.Regular);
    public static readonly Font Heading = new("Inter SemiBold", 20f, FontStyle.Bold);
    public static readonly Font SubHeading = new("Inter SemiBold", 12f, FontStyle.Bold);
    // Material Icons font (loaded via MaterialIcons helper)
    public static readonly Font IconFont = MaterialIcons.Font;

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
