from xml.dom.minidom import Childless
from enum import Enum


class ThreadStatus(Enum):
    STOPPED = 1
    RUNNING = 2
    PAUSED = 3


def get_element_data_by_tag_name(doc, tag_name, index=0, default=None) -> str:
    element = get_element_by_tag_name(doc, tag_name, index)
    child = element.firstChild
    if child is None:
        return default
    if not hasattr(child, 'data'):
        return default
    return child.data


def get_element_by_tag_name(doc, tag_name, index=0, default=Childless()):
    elements = doc.getElementsByTagName(tag_name)
    if len(elements) == 0:
        return default
    return elements[index]


def to_seconds(t: str) -> int:
    s = 0
    a = t.split(':')
    try:
        s = int(a[0]) * 60 * 60 + int(a[1]) * 60 + int(a[2])
    except:
        return 0
    return s

