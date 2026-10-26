from typing import Any

from app.services.schema_resolver import SchemaResolver


class EndpointAnalyzer:

    def analyze(
        self,
        specification: dict[str, Any]
    ) -> list[dict[str, Any]]:

        endpoints = []

        resolver = SchemaResolver(specification)

        paths = specification.get("paths", {})

        for path, path_item in paths.items():

            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():

                if method.lower() not in {
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                    "head",
                    "options",
                }:
                    continue

                if not isinstance(operation, dict):
                    continue

                endpoint = {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": operation.get(
                        "operationId"
                    ),
                    "summary": operation.get(
                        "summary"
                    ),
                    "description": operation.get(
                        "description"
                    ),
                    "tags": operation.get(
                        "tags", []
                    ),
                    "parameters": self._analyze_parameters(
                        path_item,
                        operation,
                        resolver
                    ),
                    "request_body": self._analyze_request_body(
                        operation,
                        resolver
                    ),
                    "responses": self._analyze_responses(
                        operation,
                        resolver
                    ),
                }

                endpoints.append(endpoint)

        return endpoints

    def _analyze_parameters(
        self,
        path_item: dict[str, Any],
        operation: dict[str, Any],
        resolver: SchemaResolver,
    ) -> list[dict[str, Any]]:

        parameters = []

        all_parameters = path_item.get(
            "parameters", []
        )

        all_parameters = all_parameters + operation.get(
            "parameters", []
        )

        for parameter in all_parameters:

            if not isinstance(parameter, dict):
                continue

            schema = resolver.resolve(
                parameter.get("schema")
            )

            parameters.append({
                "name": parameter.get("name"),
                "location": parameter.get("in"),
                "required": parameter.get(
                    "required",
                    False
                ),
                "type": schema.get("type")
                if schema else None,
                "format": schema.get("format")
                if schema else None,
                "example": parameter.get(
                    "example"
                ),
                "schema": schema,
            })

        return parameters

    def _analyze_request_body(
        self,
        operation: dict[str, Any],
        resolver: SchemaResolver,
    ) -> dict[str, Any] | None:

        request_body = operation.get(
            "requestBody"
        )

        if not request_body:
            return None

        content = request_body.get(
            "content",
            {}
        )

        if not content:
            return None

        content_type = next(
            iter(content)
        )

        media_type = content[
            content_type
        ]

        schema = resolver.resolve(
            media_type.get("schema")
        )

        return {
            "required": request_body.get(
                "required",
                False
            ),
            "content_type": content_type,
            "schema": schema,
        }

    def _analyze_responses(
        self,
        operation: dict[str, Any],
        resolver: SchemaResolver,
    ) -> list[dict[str, Any]]:

        responses = []

        for status_code, response in operation.get(
            "responses",
            {}
        ).items():

            response_data = {
                "status_code": status_code,
                "description": response.get(
                    "description"
                ),
            }

            content = response.get(
                "content",
                {}
            )

            if content:

                content_type = next(
                    iter(content)
                )

                media_type = content[
                    content_type
                ]

                schema = resolver.resolve(
                    media_type.get("schema")
                )

                response_data[
                    "content_type"
                ] = content_type

                response_data[
                    "schema"
                ] = schema

            responses.append(
                response_data
            )

        return responses