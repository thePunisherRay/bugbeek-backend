import time
import httpx


class TestExecutor:

    async def execute_test(self, test: dict, base_url: str) -> dict:

        method = test["method"].upper()
        original_path = test["path"]
        path = original_path

        request = test.get("request", {})

        path_params = request.get("path_params", {}) or {}
        query_params = request.get("query_params", {}) or {}
        body = request.get("body", None)

        # ---------------------------------------------------------
        # Replace path parameters
        # ---------------------------------------------------------

        for name, value in path_params.items():
            path = path.replace(
                "{" + name + "}",
                str(value)
            )

        # ---------------------------------------------------------
        # Build URL
        # ---------------------------------------------------------

        url = base_url.rstrip("/") + path

        # ---------------------------------------------------------
        # Expected status
        # ---------------------------------------------------------

        expected_status_codes = (
            test.get("expected", {})
            .get("status_codes", [])
        )

        # ---------------------------------------------------------
        # Execute request
        # ---------------------------------------------------------

        try:

            start_time = time.perf_counter()

            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0
            ) as client:

                # Don't send query parameters whose value is None
                clean_query_params = {
                    key: value
                    for key, value in query_params.items()
                    if value is not None
                }

                # -------------------------------------------------
                # Build request arguments
                # -------------------------------------------------

                request_kwargs = {
                    "method": method,
                    "url": url,
                    "params": clean_query_params,
                }

                # Only send JSON body when a body actually exists
                if body is not None:
                    request_kwargs["json"] = body

                response = await client.request(
                    **request_kwargs
                )

            response_time = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            actual_status_code = response.status_code

            passed = (
                actual_status_code
                in expected_status_codes
            )

            # ---------------------------------------------------------
            # Parse response
            # ---------------------------------------------------------

            try:
                response_body = response.json()
            except Exception:
                response_body = response.text

            # ---------------------------------------------------------
            # Result
            # ---------------------------------------------------------

            return {
                "test_id": test["test_id"],
                "name": test["name"],
                "method": method,
                "path": path,
                "category": test.get("category"),

                "status": (
                    "PASS"
                    if passed
                    else "FAIL"
                ),

                "expected_status_codes":
                    expected_status_codes,

                "actual_status_code":
                    actual_status_code,

                "response_time_ms":
                    response_time,

                "response_body":
                    response_body,
            }

        except httpx.ConnectError as exc:

            return {
                "test_id": test["test_id"],
                "name": test["name"],
                "method": method,
                "path": path,
                "category": test.get("category"),

                "status": "ERROR",

                "expected_status_codes":
                    expected_status_codes,

                "actual_status_code":
                    None,

                "response_time_ms":
                    None,

                "response_body":
                    None,

                "error":
                    f"Connection failed: {str(exc)}",
            }

        except httpx.TimeoutException as exc:

            return {
                "test_id": test["test_id"],
                "name": test["name"],
                "method": method,
                "path": path,
                "category": test.get("category"),

                "status": "ERROR",

                "expected_status_codes":
                    expected_status_codes,

                "actual_status_code":
                    None,

                "response_time_ms":
                    None,

                "response_body":
                    None,

                "error":
                    f"Request timed out: {str(exc)}",
            }

        except Exception as exc:

            return {
                "test_id": test["test_id"],
                "name": test["name"],
                "method": method,
                "path": path,
                "category": test.get("category"),

                "status": "ERROR",

                "expected_status_codes":
                    expected_status_codes,

                "actual_status_code":
                    None,

                "response_time_ms":
                    None,

                "response_body":
                    None,

                "error":
                    str(exc),
            }