from django import template

register = template.Library()

@register.filter
def in_material_types(material, materials_list):
    """
    Check if a material type exists in the list of available materials
    """
    if not material or not materials_list:
        return False
    return any(material == mat['material_type'] for mat in materials_list)

@register.filter
def get_dict_item(dictionary, key):
    """Filter to get a dictionary item by key."""
    return dictionary.get(key)

# @register.filter
# def in_material_types(material, available_materials):
#     """Check if a material is in the list of available material types."""
#     return any(material == mat.get('material_type') for mat in available_materials)