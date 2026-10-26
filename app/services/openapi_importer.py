import httpx


class OpenAPIImporter:

    async def import_from_url(self, url: str) -> dict:

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True
        ) as client:

            response = await client.get(url)

            response.raise_for_status()

            specification = response.json()

        if not isinstance(specification, dict):
            raise ValueError(
                "OpenAPI specification must be a JSON object."
            )

        if "paths" not in specification:
            raise ValueError(
                "Invalid OpenAPI specification: 'paths' not found."
            )

        return specification