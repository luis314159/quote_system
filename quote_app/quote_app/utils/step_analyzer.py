import trimesh
import numpy as np
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import pandas as pd
import re
from datetime import datetime
from io import TextIOWrapper


@dataclass
class Component:
    name: str
    volume: float
    material: Optional[str]
    vertices: int
    faces: int
    quantity: int = 1


class STEPAnalyzer:
    def __init__(self, file: TextIOWrapper):
        self.file = file
        self.logger = logging.getLogger(__name__)
        self.materials_map = self._parse_step_materials()

    def _parse_step_materials(self) -> Dict[str, str]:
        materials = {}
        try:
            self.file.seek(0)  # Asegurar que leemos desde el inicio
            content = self.file.read()
            material_pattern = r"#\d+=DESCRIPTIVE_REPRESENTATION_ITEM\('([^']+)','([^']+)'\);"
            material_matches = re.finditer(material_pattern, content)
            for match in material_matches:
                if match.group(1) == 'Steel':
                    materials[match.group(1)] = 'Steel'
            return materials
        except Exception as e:
            self.logger.error(f"Error parsing materials from STEP file: {str(e)}")
            return {}

    def calculate_volume(self, mesh: trimesh.Trimesh) -> float:
        if not mesh.is_watertight:
            self.logger.warning(f"Malla no es watertight - el volumen podría ser inexacto")

        mesh.fix_normals()
        volume = abs(mesh.volume)
        inch_conversion = (1 / 0.0254) ** 3
        return round(volume * inch_conversion, 7)

    def _clean_component_name(self, name: str) -> str:
        if '_Default<As Machined>' in name:
            base_name = name.split('_Default<As Machined>')[0]
            return f"{base_name}_Default<As Machined>"
        return name

    def analyze_components(self) -> List[Component]:
        try:
            self.file.seek(0)
            scene = trimesh.load(self.file, file_type='step')  # Procesa bytes directamente
            components_dict = {}

            if isinstance(scene, trimesh.Scene):
                for name, geometry in scene.geometry.items():
                    if isinstance(geometry, trimesh.Trimesh) and not geometry.is_empty:
                        volume = self.calculate_volume(geometry)
                        clean_name = self._clean_component_name(name)

                        if clean_name in components_dict:
                            components_dict[clean_name].quantity += 1
                        else:
                            component = Component(
                                name=clean_name,
                                volume=volume,
                                material='Steel' if 'Steel' in self.materials_map else None,
                                vertices=len(geometry.vertices),
                                faces=len(geometry.faces)
                            )
                            components_dict[clean_name] = component

            elif isinstance(scene, trimesh.Trimesh) and not scene.is_empty:
                volume = self.calculate_volume(scene)
                clean_name = self._clean_component_name("Component")
                component = Component(
                    name=clean_name,
                    volume=volume,
                    material='Steel' if 'Steel' in self.materials_map else None,
                    vertices=len(scene.vertices),
                    faces=len(scene.faces)
                )
                components_dict[clean_name] = component

            return list(components_dict.values())
        except Exception as e:
            self.logger.error(f"Error al analizar el archivo STEP: {str(e)}")
            raise


            return list(components_dict.values())
        except Exception as e:
            self.logger.error(f"Error al analizar el archivo STEP: {str(e)}")
            raise


def analyze_step_file(file: TextIOWrapper, csv_output_path: Optional[str] = "../data/csv/output") -> pd.DataFrame:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        analyzer = STEPAnalyzer(file)
        components = analyzer.analyze_components()

        if not csv_output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_output_path = f"step_analysis_{timestamp}.csv"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_output_path = f"{csv_output_path}{timestamp}.csv"

        data = [
            {
                "Component": component.name,
                "Volume (in³)": component.volume,
                "Material": component.material if component.material else 'Not specified',
                "Vertices": component.vertices,
                "Faces": component.faces,
                "Quantity": component.quantity
            }
            for component in components
        ]

        df = pd.DataFrame(data)
        df.to_csv(csv_output_path, index=False, encoding='utf-8')
        logger.info(f"Results saved to {csv_output_path}")

        return df
    except Exception as e:
        logger.error(f"Error processing STEP file: {str(e)}")
        raise

if __name__ == "__main__":
    from io import BytesIO

    # Simula la carga de un archivo STEP desde un sistema externo
    file_path = "F://aethersoft//quote_app//quote_app//quote_app//data//Final Assembly.STEP"

    # Leer el archivo como bytes
    with open(file_path, "rb") as f:
        step_file = BytesIO(f.read())

    # Analizar archivo directamente desde el objeto BytesIO
    df = analyze_step_file(step_file)

    # Trabajar con el DataFrame
    print(df)
