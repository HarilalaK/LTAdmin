"""Base des services métier : dépôts, journalisation, paramètres, erreurs ACE.

Les écrans ne contiennent aucune règle métier : ils appellent les services
et affichent les ``Result`` retournés.
"""

from __future__ import annotations

from typing import Optional, TypeVar

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import ValidationResult

T = TypeVar("T")


class ServiceBase:

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        self.db = database
        self.logger = logger
        self.journal = journal
        self.parametres = parametres

    def failure(self, operation: str, exception: BaseException) -> Result:
        error = error_helper.interpret(exception)
        self.logger.error(operation, exception)
        return Result.fail(error.message, error.code)

    def failure_value(self, operation: str, exception: BaseException) -> ResultValue:
        error = error_helper.interpret(exception)
        self.logger.error(operation, exception)
        return ResultValue.fail(error.message, error.code)

    @staticmethod
    def invalid(validation: ValidationResult) -> Result:
        return Result.fail("Vérifiez la saisie :", "VALIDATION", validation.errors)

    @staticmethod
    def invalid_value(validation: ValidationResult) -> ResultValue:
        return ResultValue.fail("Vérifiez la saisie :", "VALIDATION", validation.errors)
