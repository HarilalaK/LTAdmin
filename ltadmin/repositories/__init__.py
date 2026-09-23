"""Dépôts typés : un par agrégat, requêtes paramétrées, aucun SQL ailleurs."""

from ltadmin.repositories.admin_repository import AdminRepository  # noqa: F401
from ltadmin.repositories.referentiel_repository import ReferentielRepository  # noqa: F401
from ltadmin.repositories.staff_repository import StaffRepository  # noqa: F401
from ltadmin.repositories.student_repository import StudentRepository  # noqa: F401
from ltadmin.repositories.enrollment_repository import EnrollmentRepository  # noqa: F401
from ltadmin.repositories.evaluation_repository import EvaluationRepository  # noqa: F401
from ltadmin.repositories.exam_repository import ExamRepository  # noqa: F401
from ltadmin.repositories.planning_repository import PlanningRepository  # noqa: F401
from ltadmin.repositories.bulletin_repository import BulletinRepository  # noqa: F401
from ltadmin.repositories.finance_repository import FinanceRepository  # noqa: F401
