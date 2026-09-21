using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt des finances : tarifs, échéanciers, paiements, paie des formateurs.</summary>
public sealed class FinanceRepository : RepositoryBase
{
    public FinanceRepository(AccessDatabase database) : base(database)
    {
    }

    // ----- TARIF -----

    public Tarif? GetTarif(int idTarif)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Tarif)} WHERE {Q("ID_TARIF")} = ?",
            MapTarif, P(idTarif));

    public List<Tarif> ListTarifsByClasse(int idClasse)
        => QueryList(
            $"SELECT * FROM {Q(Tables.Tarif)} WHERE {Q("ID_CLASSE")} = ? ORDER BY {Q("TYPE_FRAIS")}",
            MapTarif, P(idClasse));

    public int InsertTarif(Tarif tarif)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Tarif)} ({Q("ID_CLASSE")}, {Q("TYPE_FRAIS")}, {Q("MONTANT")}, {Q("NB_TRANCHES")}, " +
            $"{Q("OBLIGATOIRE")}, {Q("OBSERVATION")}) VALUES (?, ?, ?, ?, ?, ?)",
            P(tarif.IdClasse), P(tarif.TypeFrais), P(tarif.Montant), P(tarif.NbTranches),
            P(tarif.Obligatoire ?? true), P(tarif.Observation));

    public int UpdateTarif(Tarif tarif)
        => Execute(
            $"UPDATE {Q(Tables.Tarif)} SET {Q("ID_CLASSE")} = ?, {Q("TYPE_FRAIS")} = ?, {Q("MONTANT")} = ?, {Q("NB_TRANCHES")} = ?, " +
            $"{Q("OBLIGATOIRE")} = ?, {Q("OBSERVATION")} = ? WHERE {Q("ID_TARIF")} = ?",
            P(tarif.IdClasse), P(tarif.TypeFrais), P(tarif.Montant), P(tarif.NbTranches),
            P(tarif.Obligatoire ?? true), P(tarif.Observation), P(tarif.IdTarif));

    public int DeleteTarif(int idTarif)
        => Execute($"DELETE FROM {Q(Tables.Tarif)} WHERE {Q("ID_TARIF")} = ?", P(idTarif));

    // ----- ECHEANCIER -----

    public Echeancier? GetEcheance(int idEcheance)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Echeancier)} WHERE {Q("ID_ECHEANCE")} = ?",
            MapEcheance, P(idEcheance));

    /// <summary>Échéances d'une inscription avec type de frais, total payé et dernier paiement.</summary>
    public List<EcheanceDetail> ListEcheancesByInscription(int idInscription)
        => QueryList(
            $"SELECT ECH.*, T.{Q("TYPE_FRAIS")} AS TYPE_FRAIS_LIB, PE.{Q("TOTAL_PAYE")}, PE.{Q("DERNIER_PAIEMENT")} " +
            $"FROM (({Q(Tables.Echeancier)} AS ECH " +
            $"LEFT JOIN {Q(SavedQueries.PaiementEcheance)} AS PE ON ECH.{Q("ID_ECHEANCE")} = PE.{Q("ID_ECHEANCE")}) " +
            $"LEFT JOIN {Q(Tables.Tarif)} AS T ON ECH.{Q("ID_TARIF")} = T.{Q("ID_TARIF")}) " +
            $"WHERE ECH.{Q("ID_INSCRIPTION")} = ? ORDER BY ECH.{Q("DATE_ECHEANCE")}, ECH.{Q("NUM_TRANCHE")}",
            MapEcheanceDetail, P(idInscription));

    public int CountByInscriptionTarif(int idInscription, int idTarif)
        => ScalarInt(
            $"SELECT COUNT(*) FROM {Q(Tables.Echeancier)} WHERE {Q("ID_INSCRIPTION")} = ? AND {Q("ID_TARIF")} = ?",
            P(idInscription), P(idTarif));

    public int MaxNumTranche(int idInscription, int idTarif)
        => ScalarInt(
            $"SELECT MAX({Q("NUM_TRANCHE")}) FROM {Q(Tables.Echeancier)} WHERE {Q("ID_INSCRIPTION")} = ? AND {Q("ID_TARIF")} = ?",
            P(idInscription), P(idTarif));

    public int InsertEcheance(Echeancier echeance)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Echeancier)} ({Q("ID_INSCRIPTION")}, {Q("ID_TARIF")}, {Q("NUM_TRANCHE")}, " +
            $"{Q("LIBELLE")}, {Q("MONTANT_DU")}, {Q("DATE_ECHEANCE")}, {Q("STATUT")}, {Q("REMISE")}) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            P(echeance.IdInscription), P(echeance.IdTarif), P(echeance.NumTranche),
            P(echeance.Libelle), P(echeance.MontantDu), P(echeance.DateEcheance),
            P(echeance.Statut), P(echeance.Remise));

    public int UpdateStatut(int idEcheance, string statut)
        => Execute(
            $"UPDATE {Q(Tables.Echeancier)} SET {Q("STATUT")} = ? WHERE {Q("ID_ECHEANCE")} = ?",
            P(statut), P(idEcheance));

    public int UpdateRemise(int idEcheance, decimal? remise)
        => Execute(
            $"UPDATE {Q(Tables.Echeancier)} SET {Q("REMISE")} = ? WHERE {Q("ID_ECHEANCE")} = ?",
            P(remise), P(idEcheance));

    public int DeleteEcheance(int idEcheance)
        => Execute($"DELETE FROM {Q(Tables.Echeancier)} WHERE {Q("ID_ECHEANCE")} = ?", P(idEcheance));

    // ----- PAIEMENT -----

    public Paiement? GetPaiement(int idPaiement)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Paiement)} WHERE {Q("ID_PAIEMENT")} = ?",
            MapPaiement, P(idPaiement));

    public List<Paiement> ListPaiementsByEcheance(int idEcheance)
        => QueryList(
            $"SELECT * FROM {Q(Tables.Paiement)} WHERE {Q("ID_ECHEANCE")} = ? ORDER BY {Q("DATE_PAIEMENT")}, {Q("ID_PAIEMENT")}",
            MapPaiement, P(idEcheance));

    public decimal TotalPayeByEcheance(int idEcheance)
        => ScalarDecimal(
            $"SELECT SUM({Q("MONTANT")}) FROM {Q(Tables.Paiement)} WHERE {Q("ID_ECHEANCE")} = ?",
            P(idEcheance)) ?? 0m;

    public bool RecuExiste(string numRecu)
        => Exists($"SELECT COUNT(*) FROM {Q(Tables.Paiement)} WHERE {Q("NUM_RECU")} = ?", P(numRecu));

    public List<string> ListRecus(string prefixe)
    {
        var table = QueryTable(
            $"SELECT {Q("NUM_RECU")} FROM {Q(Tables.Paiement)} WHERE {Q("NUM_RECU")} LIKE ?",
            P(prefixe + "%"));
        var result = new List<string>(table.Rows.Count);
        foreach (DataRow row in table.Rows)
        {
            var value = DataRowMapper.GetString(row, "NUM_RECU");
            if (!string.IsNullOrWhiteSpace(value)) result.Add(value);
        }
        return result;
    }

    public int InsertPaiement(Paiement paiement)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Paiement)} ({Q("ID_ECHEANCE")}, {Q("NUM_RECU")}, {Q("DATE_PAIEMENT")}, " +
            $"{Q("MONTANT")}, {Q("MODE_PAIE")}, {Q("REF_EXTERNE")}, {Q("CODE_UTR")}, {Q("OBSERVATION")}) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            P(paiement.IdEcheance), P(paiement.NumRecu), P(paiement.DatePaiement ?? DateTime.Now),
            P(paiement.Montant), P(paiement.ModePaie), P(paiement.RefExterne),
            P(paiement.CodeUtr), P(paiement.Observation));

    public int DeletePaiement(int idPaiement)
        => Execute($"DELETE FROM {Q(Tables.Paiement)} WHERE {Q("ID_PAIEMENT")} = ?", P(idPaiement));

    public int CountPaiements() => ScalarInt($"SELECT COUNT(*) FROM {Q(Tables.Paiement)}");

    // ----- PAIE_FORMATEUR -----

    public PaieFormateur? GetPaie(int idPaie)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.PaieFormateur)} WHERE {Q("ID_PAIE")} = ?",
            MapPaie, P(idPaie));

    public PaieFormateur? GetPaieByFormateurPeriode(int idFormateur, string periode)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.PaieFormateur)} WHERE {Q("ID_FORMATEUR")} = ? AND {Q("PERIODE")} = ?",
            MapPaie, P(idFormateur), P(periode));

    public List<PaieFormateur> ListPaiesByFormateur(int idFormateur)
        => QueryList(
            $"SELECT * FROM {Q(Tables.PaieFormateur)} WHERE {Q("ID_FORMATEUR")} = ? ORDER BY {Q("PERIODE")} DESC",
            MapPaie, P(idFormateur));

    public List<PaieFormateur> ListPaiesByPeriode(string periode)
        => QueryList(
            $"SELECT * FROM {Q(Tables.PaieFormateur)} WHERE {Q("PERIODE")} = ? ORDER BY {Q("ID_FORMATEUR")}",
            MapPaie, P(periode));

    public int InsertPaie(PaieFormateur paie)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.PaieFormateur)} ({Q("ID_FORMATEUR")}, {Q("PERIODE")}, {Q("NB_HEURES")}, " +
            $"{Q("TAUX")}, {Q("MONTANT")}, {Q("PAYE")}, {Q("DATE_PAIE")}, {Q("OBSERVATION")}) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            P(paie.IdFormateur), P(paie.Periode), P(paie.NbHeures), P(paie.Taux),
            P(paie.Montant), P(paie.Paye ?? false), P(paie.DatePaie), P(paie.Observation));

    public int UpdatePaie(PaieFormateur paie)
        => Execute(
            $"UPDATE {Q(Tables.PaieFormateur)} SET {Q("NB_HEURES")} = ?, {Q("TAUX")} = ?, {Q("MONTANT")} = ?, " +
            $"{Q("PAYE")} = ?, {Q("DATE_PAIE")} = ?, {Q("OBSERVATION")} = ? WHERE {Q("ID_PAIE")} = ?",
            P(paie.NbHeures), P(paie.Taux), P(paie.Montant),
            P(paie.Paye ?? false), P(paie.DatePaie), P(paie.Observation), P(paie.IdPaie));

    public int SetPaiePayee(int idPaie, bool paye, DateTime? datePaie)
        => Execute(
            $"UPDATE {Q(Tables.PaieFormateur)} SET {Q("PAYE")} = ?, {Q("DATE_PAIE")} = ? WHERE {Q("ID_PAIE")} = ?",
            P(paye), P(datePaie), P(idPaie));

    public int DeletePaie(int idPaie)
        => Execute($"DELETE FROM {Q(Tables.PaieFormateur)} WHERE {Q("ID_PAIE")} = ?", P(idPaie));

    // ----- Mappers -----

    public static Tarif MapTarif(DataRow row) => new()
    {
        IdTarif = DataRowMapper.GetInt32(row, "ID_TARIF"),
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        TypeFrais = DataRowMapper.GetString(row, "TYPE_FRAIS"),
        Montant = DataRowMapper.GetDecimal(row, "MONTANT"),
        NbTranches = DataRowMapper.GetInt32(row, "NB_TRANCHES"),
        Obligatoire = DataRowMapper.GetBoolean(row, "OBLIGATOIRE"),
        Observation = DataRowMapper.GetString(row, "OBSERVATION")
    };

    public static Echeancier MapEcheance(DataRow row) => new()
    {
        IdEcheance = DataRowMapper.GetInt32(row, "ID_ECHEANCE"),
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        IdTarif = DataRowMapper.GetInt32(row, "ID_TARIF"),
        NumTranche = DataRowMapper.GetInt32(row, "NUM_TRANCHE"),
        Libelle = DataRowMapper.GetString(row, "LIBELLE"),
        MontantDu = DataRowMapper.GetDecimal(row, "MONTANT_DU"),
        DateEcheance = DataRowMapper.GetDateTime(row, "DATE_ECHEANCE"),
        Statut = DataRowMapper.GetString(row, "STATUT"),
        Remise = DataRowMapper.GetDecimal(row, "REMISE")
    };

    public static EcheanceDetail MapEcheanceDetail(DataRow row) => new()
    {
        IdEcheance = DataRowMapper.GetInt32(row, "ID_ECHEANCE"),
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        IdTarif = DataRowMapper.GetInt32(row, "ID_TARIF"),
        TypeFrais = DataRowMapper.GetString(row, "TYPE_FRAIS_LIB"),
        NumTranche = DataRowMapper.GetInt32(row, "NUM_TRANCHE"),
        Libelle = DataRowMapper.GetString(row, "LIBELLE"),
        MontantDu = DataRowMapper.GetDecimal(row, "MONTANT_DU"),
        DateEcheance = DataRowMapper.GetDateTime(row, "DATE_ECHEANCE"),
        Statut = DataRowMapper.GetString(row, "STATUT"),
        Remise = DataRowMapper.GetDecimal(row, "REMISE"),
        TotalPaye = DataRowMapper.GetDecimal(row, "TOTAL_PAYE", 0m),
        DernierPaiement = DataRowMapper.GetDateTime(row, "DERNIER_PAIEMENT")
    };

    public static Paiement MapPaiement(DataRow row) => new()
    {
        IdPaiement = DataRowMapper.GetInt32(row, "ID_PAIEMENT"),
        IdEcheance = DataRowMapper.GetInt32(row, "ID_ECHEANCE"),
        NumRecu = DataRowMapper.GetString(row, "NUM_RECU"),
        DatePaiement = DataRowMapper.GetDateTime(row, "DATE_PAIEMENT"),
        Montant = DataRowMapper.GetDecimal(row, "MONTANT"),
        ModePaie = DataRowMapper.GetString(row, "MODE_PAIE"),
        RefExterne = DataRowMapper.GetString(row, "REF_EXTERNE"),
        CodeUtr = DataRowMapper.GetString(row, "CODE_UTR"),
        Observation = DataRowMapper.GetString(row, "OBSERVATION")
    };

    public static PaieFormateur MapPaie(DataRow row) => new()
    {
        IdPaie = DataRowMapper.GetInt32(row, "ID_PAIE"),
        IdFormateur = DataRowMapper.GetInt32(row, "ID_FORMATEUR"),
        Periode = DataRowMapper.GetString(row, "PERIODE"),
        NbHeures = DataRowMapper.GetDouble(row, "NB_HEURES"),
        Taux = DataRowMapper.GetDecimal(row, "TAUX"),
        Montant = DataRowMapper.GetDecimal(row, "MONTANT"),
        Paye = DataRowMapper.GetBoolean(row, "PAYE"),
        DatePaie = DataRowMapper.GetDateTime(row, "DATE_PAIE"),
        Observation = DataRowMapper.GetString(row, "OBSERVATION")
    };
}
