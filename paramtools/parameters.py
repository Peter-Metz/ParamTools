import os
import json
from collections import OrderedDict

from marshmallow import ValidationError

from paramtools.build_schema import SchemaBuilder
from paramtools import utils


class ParameterUpdateException(Exception):
    pass


class Parameters:
    schema = None
    defaults = None
    field_map = {}

    def __init__(self):
        sb = SchemaBuilder(self.schema, self.defaults, self.field_map)
        defaults, self._validator_schema = sb.build_schemas()
        for k, v in defaults.items():
            setattr(self, k, v)
        self._validator_schema.context["spec"] = self
        self.errors = {}

    def adjust(self, params_or_path, raise_errors=True, compress_errors=True):
        """
        Method to deserialize and validate parameter adjustments.
        `params_or_path` can be a file path or a `dict` that has not been
        fully deserialized. The adjusted values replace the current values
        stored in the correspondig parameter attributes.

        Raises:
            marshmallow.exceptions.ValidationError if data is not valid.
            ParameterUpdateException if dimension values do not match at
                least one existing value item's corresponding dimension values.
        """
        if isinstance(params_or_path, str) and os.path.exists(params_or_path):
            params = utils.read_json(params_or_path)
        elif isinstance(params_or_path, str):
            params = json.loads(params_or_path)
        elif isinstance(params_or_path, dict):
            params = params_or_path
        else:
            raise ValueError("params_or_path is not dict or file path")

        self.errors = {}
        # do type validation
        try:
            clean_params = self._validator_schema.load(params)
        except ValidationError as ve:
            self.format_errors(ve, compress_errors)

        # if no errors from type validation, do choice, range, etc. validation.
        if not self.errors:
            for param, value in clean_params.items():
                try:
                    self._update_param(param, value)
                except ValidationError as ve:
                    self.format_errors(ve, compress_errors)

        self._validator_schema.context["spec"] = self

        if raise_errors and self.errors:
            raise ValidationError(self.errors)

    def get(self, param, **kwargs):
        """
        Query a parameter's values along dimensions specified in `kwargs`.

        Returns: [{"value": val, "dim0": ..., }]

        Raises:
            KeyError if queried dimension is not used by this parameter.
            AttributeError if parameter does not exist.
        """
        return self._get(param, True, **kwargs)

    def specification(self, meta_data=False, **kwargs):
        """
        Query value(s) of all parameters along dimensions specified in
        `kwargs`. If `meta_data` is `True`, then parameter attributes
        are included, too.

        Returns: serialized data of shape
            {"param_name": [{"value": val, "dim0": ..., }], ...}
        """
        all_params = OrderedDict()
        for param in self._validator_schema.fields:
            result = self._get(param, False, **kwargs)
            if result:
                if meta_data:
                    param_data = getattr(self, param)
                    result = dict(param_data, **{"value": result})
                all_params[param] = result
        return all_params

    def format_errors(self, validation_error, compress_errors=True):
        """
        Format error messages from ValidationError instance. If
        `compress_errors` is `True`, all messages are collected and
        stored in a list.
        """
        if compress_errors:
            for param, messages in validation_error.messages.items():
                if param in self.errors:
                    self.errors[param].append(utils.get_leaves(messages))
                else:
                    self.errors[param] = utils.get_leaves(messages)
            validation_error.messages = self.errors
        else:
            self.errors.update(validation_error.messages)

    def _get(self, param, exact_match, **kwargs):
        """
        Private method for querying a parameter along some dimensions. If
        exact_match is True, all values in `kwargs` must be equal to the
        corresponding dimension in the parameter's "value" dictionary.

        Returns: [{"value": val, "dim0": ..., }]
        """
        value = getattr(self, param)["value"]
        ret = []
        for v in value:
            match = all(v[k] == kwargs[k] for k in kwargs
                        if (k in v or exact_match))
            if match:
                ret.append(v)
        return ret

    def _update_param(self, param, new_values):
        """
        Private method for updating the current parameter values with those
        specified by the adjustment. The values that need to be updated are
        chosen by finding all value items with dimension values matching
        the dimension values specified in the adjustment.

        Raises:
            ParameterUpdateException if dimension values do not match at
                least one existing value item's corresponding dimension values.
        """
        curr_vals = getattr(self, param)["value"]
        for i in range(len(new_values)):
            matched_at_least_once = False
            dims_to_check = tuple(k for k in new_values[i] if k != "value")
            for j in range(len(curr_vals)):
                match = all(
                    curr_vals[j][k] == new_values[i][k] for k in dims_to_check
                )
                if match:
                    matched_at_least_once = True
                    curr_vals[j]["value"] = new_values[i]["value"]
            if not matched_at_least_once:
                d = {k: new_values[i][k] for k in dims_to_check}
                raise ParameterUpdateException(
                    f"Failed to match along any of the "
                    f"following dimensions: {d}"
                )
