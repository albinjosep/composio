"""
Google AI Python Gemini tool spec.
"""

import typing as t

import typing_extensions as te
from proto.marshal.collections.maps import MapComposite
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerationResponse,
    Part,
    Tool,
)

from composio import Action, ActionType, AppType, TagType
from composio.tools import ComposioToolSet as BaseComposioToolSet
from composio.utils.shared import json_schema_to_model


class ComposioToolset(
    BaseComposioToolSet,
    runtime="google_ai",
    description_char_limit=1024,
):
    """
    Composio toolset for Google AI Python Gemini framework.

    Example:
    ```python
        import os
        import dotenv
        from vertexai.generative_models import GenerativeModel
        from composio_google import ComposioToolSet, App

        # Load environment variables from .env
        dotenv.load_dotenv()

        # Initialize tools
        composio_toolset = ComposioToolSet()

        # Get GitHub tools that are pre-configured
        tools = composio_toolset.get_tools(apps=[App.GITHUB])

        # Initialize the Gemini model
        model = GenerativeModel("gemini-pro", tools=tools)

        # Start a chat
        chat = model.start_chat()

        # Define task
        task = "Star a repo composiohq/composio on GitHub"

        # Send a message to the model
        response = chat.send_message(task)

        print(response.text)

        # Handle function calls if any
        result = composio_toolset.handle_response(response)
        if result:
            print(result)
    ```
    """

    def _wrap_tool(
        self,
        schema: t.Dict[str, t.Any],
        entity_id: t.Optional[str] = None,
    ) -> FunctionDeclaration:
        """Wraps composio tool as Google AI Python Gemini FunctionDeclaration object."""
        action = schema["name"]
        description = schema.get("description", schema["name"])
        parameters = json_schema_to_model(schema["parameters"])

        # Clean up properties by removing 'examples' field
        properties = parameters.schema().get("properties", {})
        cleaned_properties = {}
        for prop_name, prop_schema in properties.items():
            cleaned_prop = {k: v for k, v in prop_schema.items() if k != "examples"}
            cleaned_properties[prop_name] = cleaned_prop

        # Create cleaned parameters
        cleaned_parameters = {
            "type": "object",
            "properties": cleaned_properties,
            "required": parameters.schema().get("required", []),
        }

        return FunctionDeclaration(
            name=action,
            description=description,
            parameters=cleaned_parameters,
        )

    @te.deprecated("Use `ComposioToolSet.get_tools` instead")
    def get_actions(
        self,
        actions: t.Sequence[ActionType],
        entity_id: t.Optional[str] = None,
    ) -> Tool:
        """
        Get composio tools wrapped as Google AI Python Gemini FunctionDeclaration objects.

        :param actions: List of actions to wrap
        :param entity_id: Entity ID for the function wrapper

        :return: Composio tools wrapped as `FunctionDeclaration` objects
        """
        return self.get_tool(actions=actions, entity_id=entity_id)

    def get_tool(
        self,
        actions: t.Optional[t.Sequence[ActionType]] = None,
        apps: t.Optional[t.Sequence[AppType]] = None,
        tags: t.Optional[t.List[TagType]] = None,
        entity_id: t.Optional[str] = None,
    ) -> Tool:
        """
        Get composio tools wrapped as Google AI Python Gemini FunctionDeclaration objects.

        :param actions: List of actions to wrap
        :param apps: List of apps to wrap
        :param tags: Filter the apps by given tags
        :param entity_id: Entity ID for the function wrapper

        :return: Composio tools wrapped as `FunctionDeclaration` objects
        """
        self.validate_tools(apps=apps, actions=actions, tags=tags)
        return Tool(
            function_declarations=[
                self._wrap_tool(
                    schema=tool.model_dump(
                        exclude_none=True,
                    ),
                    entity_id=entity_id or self.entity_id,
                )
                for tool in self.get_action_schemas(
                    actions=actions, apps=apps, tags=tags
                )
            ]
        )

    def execute_function_call(
        self,
        function_call: t.Any,
        entity_id: t.Optional[str] = None,
    ) -> t.Dict:
        """
        Execute a function call.

        :param function_call: Function call metadata from Gemini model response.
        :param entity_id: Entity ID to use for executing the function call.
        :return: Object containing output data from the function call.
        """

        def convert_map_composite(obj):
            if isinstance(obj, MapComposite):
                return {k: convert_map_composite(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_map_composite(item) for item in obj]
            else:
                return obj

        args = convert_map_composite(function_call.args)

        return self.execute_action(
            action=Action(value=function_call.name),
            params=args,
            entity_id=entity_id or self.entity_id,
        )

    def handle_response(
        self,
        response: GenerationResponse,
        entity_id: t.Optional[str] = None,
    ) -> t.List[t.Dict]:
        """
        Handle response from Google AI Python Gemini model.

        :param response: Generation response from the Gemini model.
        :param entity_id: Entity ID to use for executing the function call.
        :return: A list of output objects from the function calls.
        """
        outputs = []
        for candidate in response.candidates:
            if hasattr(candidate.content, 'parts'):
                for part in candidate.content.parts:
                    if isinstance(part, Part) and part.function_call:
                        outputs.append(
                            self.execute_function_call(
                                function_call=part.function_call,
                                entity_id=entity_id or self.entity_id,
                            )
                        )
        return outputs

    def execute_function_call(
        self,
        function_call: t.Any,
        entity_id: t.Optional[str] = None,
    ) -> t.Dict:
        """
        Execute a function call.

        :param function_call: Function call metadata from Gemini model response.
        :param entity_id: Entity ID to use for executing the function call.
        :return: Object containing output data from the function call.
        """

        def convert_map_composite(obj):
            if isinstance(obj, MapComposite):
                return {k: convert_map_composite(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_map_composite(item) for item in obj]
            else:
                return obj

        args = convert_map_composite(function_call.args) if function_call.args is not None else {}

        return self.execute_action(
            action=Action(value=function_call.name),
            params=args,
            entity_id=entity_id or self.entity_id,
        )
