"""Composition racine : assemble la base, les dépôts et les services.

Un seul point de construction (main.py et les tests l'utilisent) ; y injecter
un moteur alternatif (SQLite pour les tests) suffit pour tester toute la
logique métier sans Access.
"""

from __future__ import annotations

from typing import Optional

from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.database_repository import DatabaseRepository
from ltadmin.services.administration.admin_service import AdminService
from ltadmin.services.auth.authentication_service import AuthenticationService
from ltadmin.services.business.bulletin_service import BulletinService
from ltadmin.services.business.eco_service import EcoService
from ltadmin.services.business.enrollment_service import EnrollmentService
from ltadmin.services.business.exam_service import ExamService
from ltadmin.services.business.evaluation_service import EvaluationService
from ltadmin.services.business.grade_service import GradeService
from ltadmin.services.business.payroll_service import PayrollService
from ltadmin.services.business.schedule_service import ScheduleService
from ltadmin.services.business.student_service import StudentService
from ltadmin.services.infrastructure.backup_service import BackupService
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.referentiel.referentiel_service import ReferentielService
from ltadmin.services.reports.report_service import ReportService
from ltadmin.services.statistics.statistics_service import StatisticsService


class AppServices:

    def __init__(self, database: AccessDatabase, logger: Optional[AppLogger] = None):
        self.database = database
        self.logger = logger or AppLogger()
        self.journal = JournalService(database, self.logger)
        self.parametres = ParametreService(database, self.journal, self.logger)
        self.authentication = AuthenticationService(database, self.journal, self.logger)
        self.admin = AdminService(database, self.logger, self.journal, self.parametres)
        self.referentiel = ReferentielService(database, self.logger, self.journal,
                                              self.parametres)
        self.students = StudentService(database, self.logger, self.journal, self.parametres)
        self.enrollments = EnrollmentService(database, self.logger, self.journal,
                                             self.parametres)
        self.evaluations = EvaluationService(database, self.logger, self.journal,
                                             self.parametres)
        self.grades = GradeService(database, self.logger, self.journal, self.parametres)
        self.bulletins = BulletinService(database, self.logger, self.journal,
                                         self.parametres)
        self.exams = ExamService(database, self.logger, self.journal, self.parametres)
        self.schedule = ScheduleService(database, self.logger, self.journal,
                                        self.parametres)
        self.ecolage = EcoService(database, self.logger, self.journal, self.parametres)
        self.payroll = PayrollService(database, self.logger, self.journal, self.parametres)
        self.statistics = StatisticsService(database, self.logger, self.parametres)
        self.reports = ReportService(database, self.logger)
        self.backups = BackupService(database, self.logger)
        self.tables = DatabaseRepository(database)

    def open(self) -> None:
        if not self.database.is_open:
            self.database.open()
        self.parametres.invalidate()

    def close(self) -> None:
        self.database.dispose()

    def refresh(self) -> None:
        """Après une restauration de sauvegarde : invalider les caches."""
        self.parametres.invalidate()

    def __enter__(self) -> "AppServices":
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False
