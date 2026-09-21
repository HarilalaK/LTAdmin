using System.Data.OleDb;

namespace LTAdmin.Data;

/// <summary>
/// Portée de transaction sur la connexion Access unique de l'application.
/// Validez avec <see cref="Complete"/> ; sans validation, la destruction
/// annule automatiquement la transaction (rollback).
/// Les imbrications ne sont pas prises en charge : Access/ACE n'offre pas
/// de transactions imbriquées via OleDb.
/// </summary>
public sealed class AccessTransaction : IDisposable
{
    private readonly AccessDatabase _database;
    private bool _completed;
    private bool _disposed;

    internal AccessTransaction(AccessDatabase database)
    {
        _database = database;
        _database.BeginTransactionInternal();
    }

    /// <summary>Valide la transaction (commit).</summary>
    public void Complete()
    {
        ThrowIfDisposed();
        if (_completed) return;
        _database.CommitInternal();
        _completed = true;
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        if (!_completed)
            _database.RollbackInternal();
    }

    private void ThrowIfDisposed()
    {
        if (_disposed) throw new ObjectDisposedException(nameof(AccessTransaction));
    }
}
