from typing import Any


class TestGenerator:

    def generate(self, specification: dict) -> list[dict]:
        tests = []
        counter = 1

        paths = specification.get("paths", {})

        for path, path_item in paths.items():

            for method, operation in path_item.items():

                if method.lower() not in {
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete"
                }:
                    continue

                method_upper = method.upper()
                operation_id = operation.get("operationId")
                summary = operation.get("summary") or f"{method_upper} {path}"

                parameters = operation.get("parameters", [])
                request_body = operation.get("requestBody")

                path_params = [
                    p for p in parameters
                    if p.get("in") == "path"
                ]

                query_params = [
                    p for p in parameters
                    if p.get("in") == "query"
                ]

                # -------------------------------------------------
                # 1. HAPPY PATH
                # -------------------------------------------------

                request = {
                    "path_params": {},
                    "query_params": {}
                }

                for parameter in path_params:
                    name = parameter["name"]
                    schema = parameter.get("schema", parameter)
                    request["path_params"][name] = self._generate_valid_value(
                        schema,
                        name
                    )

                for parameter in query_params:
                    name = parameter["name"]

                    # Optional parameters should NOT be sent
                    # unless we specifically want to test them.
                    if parameter.get("required", False):
                        schema = parameter.get("schema", parameter)
                        request["query_params"][name] = (
                            self._generate_valid_value(schema, name)
                        )

                if request_body:
                    body = self._generate_request_body(request_body)

                    request["body"] = body

                tests.append(
                    self._create_test(
                        counter,
                        method_upper,
                        path,
                        summary,
                        operation_id,
                        "happy_path",
                        request,
                        self._expected_status(operation)
                    )
                )

                counter += 1

                # -------------------------------------------------
                # 2. NEGATIVE PARAMETER TESTS
                # -------------------------------------------------

                for parameter in path_params + query_params:

                    schema = parameter.get(
                        "schema",
                        parameter
                    )

                    invalid_value = self._generate_invalid_value(schema)

                    negative_request = {
                        "path_params": dict(
                            request["path_params"]
                        ),
                        "query_params": dict(
                            request["query_params"]
                        )
                    }

                    name = parameter["name"]

                    if parameter.get("in") == "path":
                        negative_request["path_params"][name] = (
                            invalid_value
                        )
                    else:
                        negative_request["query_params"][name] = (
                            invalid_value
                        )

                    tests.append(
                        self._create_test(
                            counter,
                            method_upper,
                            path,
                            f"{summary} - invalid {parameter['in']} parameter: {name}",
                            operation_id,
                            "validation",
                            negative_request,
                            [422],
                            reason=(
                                f"Parameter '{name}' receives a value "
                                f"incompatible with its declared OpenAPI type."
                            )
                        )
                    )

                    counter += 1

                # -------------------------------------------------
                # 3. BODY VALIDATION TESTS
                # -------------------------------------------------

                if request_body:

                    schema = self._get_body_schema(request_body)

                    if schema:

                        required_fields = schema.get(
                            "required",
                            []
                        )

                        # Missing required field
                        for field in required_fields:

                            invalid_body = self._generate_valid_object(
                                schema
                            )

                            invalid_body.pop(field, None)

                            body_request = {
                                "path_params": dict(
                                    request["path_params"]
                                ),
                                "query_params": dict(
                                    request["query_params"]
                                ),
                                "body": invalid_body
                            }

                            tests.append(
                                self._create_test(
                                    counter,
                                    method_upper,
                                    path,
                                    f"{summary} - missing required field: {field}",
                                    operation_id,
                                    "validation",
                                    body_request,
                                    [422],
                                    reason=(
                                        f"Required request-body field "
                                        f"'{field}' is omitted."
                                    )
                                )
                            )

                            counter += 1

                        # Invalid value for fields
                        for field, field_schema in schema.get(
                            "properties",
                            {}
                        ).items():

                            invalid_value = self._generate_invalid_value(
                                field_schema
                            )

                            invalid_body = self._generate_valid_object(
                                schema
                            )

                            invalid_body[field] = invalid_value

                            body_request = {
                                "path_params": dict(
                                    request["path_params"]
                                ),
                                "query_params": dict(
                                    request["query_params"]
                                ),
                                "body": invalid_body
                            }

                            tests.append(
                                self._create_test(
                                    counter,
                                    method_upper,
                                    path,
                                    f"{summary} - invalid field: {field}",
                                    operation_id,
                                    "validation",
                                    body_request,
                                    [422],
                                    reason=(
                                        f"Field '{field}' receives a value "
                                        f"incompatible with its OpenAPI schema."
                                    )
                                )
                            )

                            counter += 1

                # -------------------------------------------------
                # 4. BOUNDARY TESTS
                # -------------------------------------------------

                for parameter in path_params:

                    schema = parameter.get(
                        "schema",
                        parameter
                    )

                    if schema.get("type") in {
                        "integer",
                        "number"
                    }:

                        name = parameter["name"]

                        for value in [0, -1]:

                            boundary_request = {
                                "path_params": dict(
                                    request["path_params"]
                                ),
                                "query_params": dict(
                                    request["query_params"]
                                )
                            }

                            boundary_request["path_params"][name] = value

                            tests.append(
                                self._create_test(
                                    counter,
                                    method_upper,
                                    path,
                                    f"{summary} - {name} = {value}",
                                    operation_id,
                                    "boundary",
                                    boundary_request,
                                    self._expected_status(operation),
                                    reason=(
                                        f"Boundary value generated for "
                                        f"numeric parameter '{name}'."
                                    )
                                )
                            )

                            counter += 1

        return tests

    # =============================================================
    # TEST CREATION
    # =============================================================

    def _create_test(
        self,
        counter: int,
        method: str,
        path: str,
        name: str,
        operation_id: str,
        category: str,
        request: dict,
        expected_status: list[int],
        reason: str | None = None
    ) -> dict:

        result = {
            "test_id": f"TC-{counter:03d}",
            "method": method,
            "path": path,
            "name": name,
            "category": category,
            "operation_id": operation_id,
            "request": request,
            "expected": {
                "status_codes": expected_status
            }
        }

        if reason:
            result["reason"] = reason

        return result

    # =============================================================
    # REQUEST BODY
    # =============================================================

    def _generate_request_body(
        self,
        request_body: dict
    ) -> dict:

        schema = self._get_body_schema(request_body)

        if not schema:
            return {}

        return self._generate_valid_object(schema)

    def _get_body_schema(
        self,
        request_body: dict
    ) -> dict:

        content = request_body.get("content", {})

        json_content = content.get(
            "application/json"
        )

        if not json_content:
            return {}

        return json_content.get(
            "schema",
            {}
        )

    def _generate_valid_object(
        self,
        schema: dict
    ) -> dict:

        properties = schema.get(
            "properties",
            {}
        )

        required = schema.get(
            "required",
            []
        )

        result = {}

        for field, field_schema in properties.items():

            if field in required:
                result[field] = self._generate_valid_value(
                    field_schema,
                    field
                )

        return result

    # =============================================================
    # VALUE GENERATION
    # =============================================================

    def _generate_valid_value(
        self,
        schema: dict,
        field_name: str = ""
    ) -> Any:

        if "$ref" in schema:
            return {}

        if "example" in schema:
            return schema["example"]

        if "default" in schema:
            return schema["default"]

        if "enum" in schema and schema["enum"]:
            return schema["enum"][0]

        schema_type = schema.get("type")

        if schema_type == "string":

            fmt = schema.get("format")

            if fmt == "email":
                return "testuser@example.com"

            if fmt == "date":
                return "2026-01-01"

            if fmt == "date-time":
                return "2026-01-01T10:00:00Z"

            min_length = schema.get("minLength", 1)

            return (
                "Test "
                + "User"
            )[:max(min_length, 2)]

        if schema_type == "integer":

            if "minimum" in schema:
                return schema["minimum"]

            return 1

        if schema_type == "number":

            if "minimum" in schema:
                return schema["minimum"]

            return 99.99

        if schema_type == "boolean":
            return True

        if schema_type == "array":

            items = schema.get(
                "items",
                {}
            )

            return [
                self._generate_valid_value(
                    items,
                    field_name
                )
            ]

        if schema_type == "object":

            return self._generate_valid_object(
                schema
            )

        return "test-value"

    # =============================================================
    # INVALID VALUES
    # =============================================================

    def _generate_invalid_value(
        self,
        schema: dict
    ) -> Any:

        schema_type = schema.get("type")

        if schema_type == "integer":
            return "not-an-integer"

        if schema_type == "number":
            return "not-a-number"

        if schema_type == "boolean":
            return "not-a-boolean"

        if schema_type == "array":
            return "not-an-array"

        if schema_type == "object":
            return "not-an-object"

        if schema_type == "string":

            if schema.get("format") == "email":
                return "not-an-email"

            return 12345

        return None

    # =============================================================
    # EXPECTED STATUS
    # =============================================================

    def _expected_status(
        self,
        operation: dict
    ) -> list[int]:

        responses = operation.get(
            "responses",
            {}
        )

        success_codes = []

        for code in responses.keys():

            try:
                status = int(code)

                if 200 <= status < 300:
                    success_codes.append(status)

            except (ValueError, TypeError):
                continue

        if success_codes:
            return success_codes

        return [200]