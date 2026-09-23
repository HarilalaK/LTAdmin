using System.Drawing;

namespace LTAdmin.UI;

/// <summary>
/// Simple helper to provide a Font for Material Icons.
/// In a full implementation you would embed the Material Icons TTF file and load it here.
/// For now we fall back to a system icon font (Segoe MDL2 Assets) which is available on Windows.
/// </summary>
internal static class MaterialIcons
{
    public static readonly Font Font = new Font("Segoe MDL2 Assets", 12f, FontStyle.Regular);
}
