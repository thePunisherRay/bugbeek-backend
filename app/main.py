from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal

from pydantic import BaseModel, HttpUrl

from app.services.endpoint_analyzer import EndpointAnalyzer
from app.services.openapi_importer import OpenAPIImporter
from app.services.test_generator import TestGenerator
from app.services.test_executor import TestExecutor


app = FastAPI(
    title="BUGSHOT",
    description="AI-powered API quality engineering platform",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ImportRequest(BaseModel):
    type: Literal["curl", "yaml", "url"]
    content: str  # cURL command, YAML/JSON document text, or a URL


class TestGenerationRequest(BaseModel):
    specification: dict

class ExecuteRequest(BaseModel):
    base_url: HttpUrl
    tests: list[dict]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "product": "BUGSHOT",
        "version": "0.1.0",
    }


@app.post("/api/import")
async def import_openapi(request: ImportRequest):

    importer = OpenAPIImporter()

    try:
        content = request.content.strip()

        if not content:
            raise ValueError("Input is empty")

        if request.type == "curl":
            specification = importer.import_from_curl(content)
        elif request.type == "yaml":
            specification = importer.import_from_text(content)
        else:
            specification = await importer.import_from_url(content)

        endpoints = EndpointAnalyzer().analyze(specification)

        servers = specification.get("servers") or []
        base_url = (
            servers[0].get("url")
            if servers and isinstance(servers[0], dict)
            else None
        )

        return {
            "success": True,
            "source": request.type,
            "title": specification.get("info", {}).get("title"),
            "version": specification.get("info", {}).get("version"),
            "openapi_version": specification.get(
                "openapi",
                specification.get("swagger")
            ),
            "base_url": base_url,
            "endpoint_count": len(endpoints),
            "endpoints": endpoints,
            # Fully dereferenced; send this to /api/generate-tests
            "specification": specification,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.post("/api/generate-tests")
async def generate_tests(request: TestGenerationRequest):

    try:
        generator = TestGenerator()

        tests = generator.generate(request.specification)

        return {
            "success": True,
            "product": "BUGSHOT",
            "test_count": len(tests),
            "tests": tests,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

@app.post("/api/execute")
async def execute_tests(request: ExecuteRequest):

    executor = TestExecutor()

    results = []

    for test in request.tests:
        result = await executor.execute_test(
            test,
            str(request.base_url)
        )

        results.append(result)

    passed = sum(
        1 for result in results
        if result["status"] == "PASS"
    )

    failed = sum(
        1 for result in results
        if result["status"] == "FAIL"
    )

    errors = sum(
        1 for result in results
        if result["status"] == "ERROR"
    )

    return {
        "success": True,
        "product": "BUGSHOT",
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": round(
                (passed / len(results)) * 100, 2
            ) if results else 0
        },
        "results": results
    }