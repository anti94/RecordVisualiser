"""Profil C oturumu: şema yükleme ve kayıt açma — `F7-048`…`F7-050`.

Profil C bir kaydı açmak için **iki** girdiye ihtiyaç duyar: klasör ve
şema. Şema C++ struct tanımlarının tarifidir (`D-29`) ve her kurulumda
farklı olabilir; bu yüzden koda gömülmez, ayarlardan gelir.

Bu modül ikisini birleştirir ve **her başarısızlığı adlandırır**. Şema
yolu boşsa, dosya yoksa, şema geçersizse ya da şema kayıtla uyuşmuyorsa
kullanıcı hangisi olduğunu görür. Hepsi tek bir "kayıt açılamadı"
mesajına indirilseydi, kullanıcı neyi düzelteceğini bilemezdi.

Qt'ye bağlı değildir: oturum mantığı arayüzden ayrı sınanabilmelidir.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sonar_analyzer.io.decoders.profile_c_folder import FolderError
from sonar_analyzer.io.schema.errors import SchemaError
from sonar_analyzer.io.schema.loader import load as load_schema
from sonar_analyzer.io.schema.messages import SchemaErrorReport, describe, describe_warnings
from sonar_analyzer.io.schema.model import Schema
from sonar_analyzer.repository.folder_repository import FolderRecordingRepository


class OpenFailure(Enum):
    """Bir Profil C kaydının açılamama nedeni."""

    NO_SCHEMA_CONFIGURED = "sema secilmemis"
    SCHEMA_FILE_MISSING = "sema dosyasi yok"
    SCHEMA_INVALID = "sema gecersiz"
    FOLDER_INVALID = "klasor bir kayit degil"
    SCHEMA_MISMATCH = "sema kayitla uyusmuyor"


@dataclass(frozen=True)
class OpenResult:
    """Açma denemesinin sonucu.

    Başarılıysa `repository` doludur. Başarısızsa `failure` **hangi**
    adımın düştüğünü söyler ve `report` kullanıcıya gösterilecek üç
    parçalı mesajı taşır.
    """

    repository: FolderRecordingRepository | None = None
    schema: Schema | None = None
    failure: OpenFailure | None = None
    report: SchemaErrorReport | None = None
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.repository is not None


def load_configured_schema(schema_path: str) -> tuple[Schema | None, OpenResult | None]:
    """Ayarlardaki şemayı yükler; sorun varsa hazır bir sonuç döndürür."""
    if not schema_path.strip():
        return None, OpenResult(
            failure=OpenFailure.NO_SCHEMA_CONFIGURED,
            report=SchemaErrorReport(
                title="Profil C şeması seçilmemiş",
                detail=(
                    "Klasör tabanlı bir kayıt, dosyaların yerleşimini tarif eden bir TOML "
                    "şeması olmadan okunamaz. Şema C++ tarafının struct tanımlarından gelir "
                    "ve her kurulumda farklı olabilir; bu yüzden uygulamaya gömülü değildir."
                ),
                action="Settings → Profil C şeması bölümünden bir `.toml` dosyası seçin.",
            ),
        )

    path = Path(schema_path)
    if not path.is_file():
        return None, OpenResult(
            failure=OpenFailure.SCHEMA_FILE_MISSING,
            report=SchemaErrorReport(
                title="Şema dosyası bulunamadı",
                detail=(
                    f"Ayarlarda kayıtlı yol: {path}. Dosya taşınmış, silinmiş ya da "
                    f"başka bir makinede kalmış olabilir."
                ),
                action="Settings → Profil C şeması bölümünden dosyayı yeniden seçin.",
            ),
        )

    try:
        schema = load_schema(path)
    except SchemaError as error:
        return None, OpenResult(failure=OpenFailure.SCHEMA_INVALID, report=describe(error))
    return schema, None


def open_recording(folder: Path, schema_path: str) -> OpenResult:
    """Bir Profil C kayıt klasörünü açar.

    Şema ile kayıt uyuşmazsa kayıt **açılmaz** ve hata gösterilir; bu
    `docs/format/profile-c.md` §7'deki üç kapının uygulamadaki karşılığı.
    Sessizce açmak, yanlış veriyle çalışılan bir analiz oturumu demektir.
    """
    schema, failure = load_configured_schema(schema_path)
    if failure is not None:
        return failure
    assert schema is not None

    repository = FolderRecordingRepository()
    try:
        repository.open(folder, schema)
    except FolderError as error:
        return OpenResult(
            failure=OpenFailure.FOLDER_INVALID,
            report=SchemaErrorReport(
                title="Kayıt klasörü tanınmadı",
                detail=(
                    f"{error}. Profil C kaydı, altında `Tx/` ya da `Rx/` bulunan bir "
                    f"klasördür; içindeki dosyalar `RxData00000.bin` biçiminde adlandırılır."
                ),
                action="Kayıt klasörünün kendisini seçin, üst klasörünü değil.",
            ),
        )
    except SchemaError as error:
        return OpenResult(
            failure=OpenFailure.SCHEMA_MISMATCH,
            schema=schema,
            report=describe(error),
        )

    return OpenResult(
        repository=repository,
        schema=schema,
        warnings=repository.warnings,
    )


def schema_summary(schema: Schema, folder: Path) -> dict[str, str]:
    """Kayıt kartında gösterilecek özet — `F7-052`.

    Şema kimliği kartta **görünür** olmalı: aynı klasör iki farklı şemayla
    açıldığında iki farklı sonuç verir ve hangisinin kullanıldığı ekrandan
    anlaşılamazsa, yanlış olan fark edilmez.
    """
    return {
        "Klasör": folder.name,
        "Şema": f"{schema.id} v{schema.version}",
        "Sensör": str(schema.payload.sensor_count),
        "Frame örneği": str(schema.payload.frame_samples),
        "Örnek tipi": schema.payload.sample_type.cpp,
        "Yerleşim": schema.payload.layout,
    }


def warning_report(warnings: tuple[str, ...]) -> SchemaErrorReport | None:
    """Açma uyarılarını tek bir rapora toplar; uyarı yoksa `None`."""
    return describe_warnings(warnings)
