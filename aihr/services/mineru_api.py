from __future__ import annotations

import http.client
import io
import json
import os
import re
import time
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

MINERU_API_BASE = "https://mineru.net/api/v4"
DEFAULT_BATCH_SIZE = 50
MAX_BATCH_SIZE = 200


class MinerUError(RuntimeError):
    pass


@dataclass
class MinerUParsedFile:
    file_path: str
    file_name: str
    data_id: str
    state: str
    text: str = ""
    full_zip_url: str = ""
    err_msg: str = ""


def mineru_is_enabled() -> bool:
    return bool(_get_api_token())


def extract_pdf_text_with_mineru(file_path: str | Path) -> str:
    result = extract_pdf_texts_with_mineru([file_path]).get(str(Path(file_path)))
    return (result.text if result else "").strip()


def extract_pdf_texts_with_mineru(file_paths: Iterable[str | Path]) -> dict[str, MinerUParsedFile]:
    if not mineru_is_enabled():
        return {}

    normalized_paths = [Path(file_path) for file_path in file_paths]
    normalized_paths = [path for path in normalized_paths if path.exists() and path.suffix.lower() == ".pdf"]
    if not normalized_paths:
        return {}

    batch_size = min(max(_get_int_env("AIHR_MINERU_BATCH_SIZE", DEFAULT_BATCH_SIZE), 1), MAX_BATCH_SIZE)
    extracted: dict[str, MinerUParsedFile] = {}

    for chunk_start in range(0, len(normalized_paths), batch_size):
        chunk = normalized_paths[chunk_start : chunk_start + batch_size]
        extracted.update(_extract_pdf_batch(chunk))

    return extracted


def _extract_pdf_batch(file_paths: list[Path]) -> dict[str, MinerUParsedFile]:
    response = _request_json(
        method="POST",
        url=f"{MINERU_API_BASE}/file-urls/batch",
        payload={
            "enable_formula": False,
            "enable_table": False,
            "language": os.getenv("AIHR_MINERU_LANGUAGE", "ch").strip() or "ch",
            "model_version": os.getenv("AIHR_MINERU_MODEL_VERSION", "vlm").strip() or "vlm",
            "files": [
                {
                    "name": file_path.name,
                    "data_id": _build_data_id(file_path, index),
                    "is_ocr": _get_bool_env("AIHR_MINERU_ENABLE_OCR", True),
                }
                for index, file_path in enumerate(file_paths, start=1)
            ],
        },
    )

    payload = response.get("data") or {}
    batch_id = payload.get("batch_id")
    upload_urls = payload.get("file_urls") or []

    if not batch_id or len(upload_urls) != len(file_paths):
        raise MinerUError("MinerU 未返回可用的批量上传信息。")

    by_data_id = {
        _build_data_id(file_path, index): file_path
        for index, file_path in enumerate(file_paths, start=1)
    }

    for upload_url, file_path in zip(upload_urls, file_paths):
        _upload_file(upload_url, file_path)

    results = _poll_batch_results(batch_id)
    parsed: dict[str, MinerUParsedFile] = {}

    for item in results:
        data_id = str(item.get("data_id") or "")
        file_name = str(item.get("file_name") or "")
        file_path = by_data_id.get(data_id)
        if file_path is None:
            file_path = next((candidate for candidate in file_paths if candidate.name == file_name), None)
        if file_path is None:
            continue

        state = str(item.get("state") or "failed")
        full_zip_url = str(item.get("full_zip_url") or "")
        err_msg = str(item.get("err_msg") or "")
        text = ""
        if state == "done" and full_zip_url:
            text = _download_markdown_text(full_zip_url)
        parsed[str(file_path)] = MinerUParsedFile(
            file_path=str(file_path),
            file_name=file_path.name,
            data_id=data_id,
            state=state,
            text=text,
            full_zip_url=full_zip_url,
            err_msg=err_msg,
        )

    for index, file_path in enumerate(file_paths, start=1):
        key = str(file_path)
        if key in parsed:
            continue
        parsed[key] = MinerUParsedFile(
            file_path=key,
            file_name=file_path.name,
            data_id=_build_data_id(file_path, index),
            state="failed",
            err_msg="MinerU 未返回该文件的解析结果。",
        )

    return parsed


def _poll_batch_results(batch_id: str) -> list[dict]:
    deadline = time.time() + _get_int_env("AIHR_MINERU_POLL_TIMEOUT_SECONDS", 180)
    poll_interval = max(float(os.getenv("AIHR_MINERU_POLL_INTERVAL_SECONDS", "2")), 0.5)

    while time.time() < deadline:
        payload = _request_json(
            method="GET",
            url=f"{MINERU_API_BASE}/extract-results/batch/{batch_id}",
        )
        data = payload.get("data") or {}
        results = data.get("extract_result") or []
        if isinstance(results, dict):
            results = [results]

        if results and all((item.get("state") or "").lower() in {"done", "failed"} for item in results):
            return results

        time.sleep(poll_interval)

    raise MinerUError(f"MinerU 批量任务 {batch_id} 轮询超时。")


def _download_markdown_text(full_zip_url: str) -> str:
    with urlopen(full_zip_url, timeout=_get_request_timeout()) as response:
        archive_bytes = response.read()

    with ZipFile(io.BytesIO(archive_bytes)) as archive:
        markdown_members = [name for name in archive.namelist() if name.endswith("full.md")]
        if not markdown_members:
            markdown_members = [name for name in archive.namelist() if name.endswith(".md")]
        if not markdown_members:
            raise MinerUError("MinerU 结果压缩包中未找到可用的 Markdown 文本。")

        member_name = sorted(markdown_members, key=len)[0]
        markdown = archive.read(member_name).decode("utf-8", errors="ignore")

    return _markdown_to_text(markdown)


def _markdown_to_text(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n")
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = text.replace("|", " ")
    text = text.replace("`", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _upload_file(upload_url: str, file_path: Path) -> None:
    target = urlsplit(upload_url)
    connection_class = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
    path = target.path or "/"
    if target.query:
        path = f"{path}?{target.query}"

    connection = connection_class(target.netloc, timeout=_get_request_timeout())
    try:
        with file_path.open("rb") as handle:
            body = handle.read()
        headers = {
            "Content-Length": str(file_path.stat().st_size),
        }
        connection.request("PUT", path, body=body, headers=headers)
        response = connection.getresponse()
        status = getattr(response, "status", 200)
        response_body = response.read().decode("utf-8", errors="ignore")
        if status >= 400:
            raise MinerUError(f"上传 {file_path.name} 到 MinerU 失败，状态码 {status}。{response_body[:300]}")
    finally:
        connection.close()


def _request_json(method: str, url: str, payload: dict | None = None) -> dict:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {_get_api_token()}",
    }
    user_token = os.getenv("AIHR_MINERU_USER_TOKEN", "").strip()
    if user_token:
        headers["token"] = user_token

    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    request = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(request, timeout=_get_request_timeout()) as response:
            body = response.read().decode("utf-8", errors="ignore")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise MinerUError(f"MinerU 接口请求失败：HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise MinerUError(f"MinerU 接口网络异常：{exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MinerUError(f"MinerU 返回了不可解析的 JSON：{body[:200]}") from exc

    if parsed.get("code") not in {0, "0", None}:
        raise MinerUError(f"MinerU 接口返回失败：{parsed}")
    return parsed


def _build_data_id(file_path: Path, index: int) -> str:
    digest = sha1(f"{file_path.name}|{file_path.stat().st_size}|{index}".encode("utf-8")).hexdigest()[:10]
    return f"aihr-{index}-{digest}"


def _get_api_token() -> str:
    return (
        os.getenv("AIHR_MINERU_API_TOKEN", "").strip()
        or os.getenv("MINERU_API_TOKEN", "").strip()
    )


def _get_request_timeout() -> int:
    return _get_int_env("AIHR_MINERU_REQUEST_TIMEOUT_SECONDS", 60)


def _get_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default
