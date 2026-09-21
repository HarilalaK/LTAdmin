namespace LTAdmin.UI;

/// <summary>Vue capable de recharger ses données (bouton « Actualiser »).</summary>
public interface IRefreshableView
{
    void RefreshData();
}
