import enum
import os
import sys
import json


class Materials:
    def __init__(self):
        self.dir = os.path.abspath(os.path.dirname(__file__)) + os.sep + "materials"
        self.materials = {}
        for file in os.listdir(self.dir):
            if file.lower().endswith(".json"):
                with open(self.dir + os.sep + file, "r", encoding="utf-8") as f:
                    material_json = json.load(f)
                    self.materials[file.lower()[:-5]] = material_json

    def get_materials(self):
        materials = []
        for m in self.materials:
            materials.append((m, m, ""))
        return materials

    def get_float_values(self, material_name):
        float_values = []
        for m in self.materials:
            if m == material_name:
                if (
                    "Float Value"
                    in self.materials[m]["Material"]["Instance"][0]["Binder"][0]
                ):
                    for prop in self.materials[m]["Material"]["Instance"][0]["Binder"][
                        0
                    ]["Float Value"]:
                        if not isinstance(prop["Value"], list):
                            float_values.append(prop)
        return float_values

    def get_color_values(self, material_name):
        for m in self.materials:
            if m == material_name:
                if "Color" in self.materials[m]["Material"]["Instance"][0]["Binder"][0]:
                    return self.materials[m]["Material"]["Instance"][0]["Binder"][0][
                        "Color"
                    ]
        return []

    def get_instance_flags(self, material_name):
        for m in self.materials:
            if m == material_name:
                if "Instance" in self.materials[m]["Flags"]:
                    return self.materials[m]["Flags"]["Instance"]
        return []

    def get_class_flags(self, material_name):
        for m in self.materials:
            if m == material_name:
                if "Class" in self.materials[m]["Flags"]:
                    return self.materials[m]["Flags"]["Class"]
        return []
