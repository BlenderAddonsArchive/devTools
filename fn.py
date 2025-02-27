import bpy
import subprocess
import sys
from types import ModuleType
from pathlib import Path
from sys import platform
from os.path import isfile, dirname, normpath, exists
from shutil import which
from math import sqrt

def get_addon_prefs():
    import os
    addon_name = os.path.splitext(__name__)[0]
    preferences = bpy.context.preferences
    addon_prefs = preferences.addons[addon_name].preferences
    return (addon_prefs)

def get_external_editor():
    editor = get_addon_prefs().external_editor.strip()
    if not editor:
        # Fallback to text editor (in general prefs since Blender 4.0.0)
        editor = getattr(bpy.context.preferences.filepaths, 'text_editor', None).strip()

    return editor

# unused
def copy_to_clipboard():
    '''Copy selected Text to clipboard'''
    bpy.ops.text.copy()
    clip = bpy.context.window_manager.clipboard
    return (clip)

def open_file(filepath):
    '''open the file at the path given with cmd relative to user's OS'''

    editor = get_external_editor()

    if not filepath:
        return('No file path !')
    
    if not exists(filepath):
        return(f'Not exists: {filepath}')

    if editor:
        cmd = editor.strip()
    else:
        myOS = platform
        if myOS.startswith('linux') or myOS.startswith('freebsd'):# linux
            cmd = 'xdg-open'
        elif myOS.startswith('win'):# Windows
            cmd = 'start'
        else:# OS X
            cmd = 'open'

    mess = cmd + ' ' + filepath
    fullcmd = [cmd, filepath]

    print('Command :', fullcmd)

    try:
        # subprocess.Popen(fullcmd)
        # subprocess.call(fullcmd, shell=True)
        subprocess.call(fullcmd, shell=platform.startswith('win'))
    
    except:
        print('--/traceback--')
        import traceback
        traceback.print_exc()
        print('--traceback/--')
        # mess = 'Text editor not found ' + mess
        return {'CANCELLED'}

    return mess


## Open folder and select file if pointed to one
def open_folder(folderpath):
    """open the folder at the path given
    with cmd relative to user's OS
    on window, some linux, select the file if pointed
    """

    from sys import platform
    import subprocess

    ## resolve symlink

    myOS = platform
    if myOS.startswith(('linux','freebsd')):
        cmd = 'xdg-open'

    elif myOS.startswith('win'):
        cmd = 'explorer'
        if not folderpath:
            return('/')
    else:
        cmd = 'open'

    if not folderpath:
        return('//')

    if isfile(folderpath): # When pointing to a file
        select = False
        if myOS.startswith('win'):
            # Keep same path but add "/select" the file (windows cmd option)
            cmd = 'explorer /select,'
            select = True

        elif myOS.startswith(('linux','freebsd')):
            if which('nemo'):
                cmd = 'nemo --no-desktop'
                select = True
            elif which('nautilus'):
                cmd = 'nautilus --no-desktop'
                select = True

        if not select:
            # Use directory of the file
            folderpath = dirname(folderpath)
 
    ## Resolve potential symlink folder
    folderpath = Path(folderpath).resolve().as_posix()

    folderpath = normpath(folderpath)
    fullcmd = cmd.split() + [folderpath]
    # print('Opening command :', fullcmd)
    subprocess.Popen(fullcmd)
    return ' '.join(fullcmd)


""" ## just open folder (replaced by func above)
def openFolder(folderpath):
    myOS = platform
    if myOS.startswith(('linux','freebsd')):
        cmd = 'xdg-open'
    elif myOS.startswith('win'):
        cmd = 'explorer'
        if not folderpath:
            return('/')
    else:
        cmd = 'open'

    if not folderpath:
        return('//')

    fullcmd = [cmd, folderpath]
    print(fullcmd)
    subprocess.Popen(fullcmd)
    return ' '.join(fullcmd)
"""


def get_text(context):
    '''get current text and override for text editor operator'''
    text = getattr(bpy.context.space_data, "text", None)

    #context override for the ops.text.insert() function
    override = {'window': context.window,
                'area'  : context.area,
                'region': context.region,
                'space': context.space_data,
                'edit_text' : text
                }
    return(text, override)

def set_file_in_text_editor(filepath, linum=None, context=None):
    context = context or bpy.context
    print('context.area.type: ', context.area.type)
    for t in [t for t in bpy.data.texts if t.filepath == filepath] :
        bpy.data.texts.remove(t)

    text = bpy.data.texts.load(filepath)

    areas = []
    text_editor = None
    for area in context.screen.areas :
        if area.type == 'TEXT_EDITOR' :
            text_editor = area

        else :
            areas.append(area)
    if not text_editor :
        if context.area.type == 'TOPBAR':
            ## Topbar can't be splitted
            ## fallback to first 3d view found (usually the bigger area)
            text_editor = next((area for area in context.screen.areas if area.type == 'VIEW_3D'), None)
            
            if text_editor is None:
                ## fallback to any area big that is not topbar
                # text_editor = next((area for area in context.screen.areas if area.type != 'TOPBAR'), None)
                valid_area = [a for a in areas if a.type != 'TOPBAR' and a.width > 30 and a.height > 30]
                valid_area.sort(key=lambda x: sqrt(x.width**2 + x.height**2)) # filter by diagonal
                text_editor = valid_area[-1]
        
            with bpy.context.temp_override(area=text_editor):
                bpy.ops.screen.area_split(direction = "VERTICAL")

        else:
            bpy.ops.screen.area_split(direction = "VERTICAL")

        for area in context.screen.areas :
            if area not in areas :
                text_editor = area
                text_editor.type = "TEXT_EDITOR"
                text_editor.spaces[0].show_syntax_highlight = True
                text_editor.spaces[0].show_word_wrap = True
                text_editor.spaces[0].show_line_numbers = True
                context_copy = context.copy()
                context_copy['area'] = text_editor

    text_editor.spaces[0].text = text
    if linum:
        text.cursor_set(linum-1)
        ## this also force the scroll to jump where the caret is
        ## owtherwise stay at the top of the document
        with bpy.context.temp_override(area=text_editor):
            bpy.ops.text.move(type='LINE_BEGIN')

def install_pip_module(module: str):
    # get path to blender python
    pybin = sys.executable
    # ensure pip is installed
    cmd = [pybin, '-m', 'ensurepip']
    subprocess.call(cmd)
    # install module
    cmd = [pybin, '-m', 'pip', 'install', module]
    subprocess.call(cmd)

## Get source addon from idname
def get_module_path(mod):
    str_path = str(mod).rsplit("'",1)[0].split("'")[-1]
    return Path(str_path).parent.as_posix()
    # if str_path.endswith('.__init__.py'):
    #     return Path(str_path).parent.as_posix()
    # else:
    #     return Path(str_path).as_posix()

exclude_mods = ('bpy', 'os', 'subprocess', 'shutil', 're', 'sys', 'math')

def get_mod_classes(mod, classes=None, mod_path=None, depth=0):
    if classes is None:
        classes = []
        mod_path = get_module_path(mod)
    if depth > 3:
        return
    if not isinstance(mod, ModuleType):
        return
    if not get_module_path(mod).startswith(mod_path):
        return
    
    ## Old method (works only when classes are stored in a "classes" variables)
    # classes += list(getattr(mod, "classes", []))
    # for attr in dir(mod):
    #     if not attr.startswith('__') and not attr in exclude_mods:
    #         submod = getattr(mod, attr)
    #         get_mod_classes(submod, classes=classes, mod_path=mod_path, depth=depth+1)

    ## Scan module attributes for class definitions
    for attr in dir(mod):
        if attr.startswith('__') or attr in exclude_mods:
            continue
            
        item = getattr(mod, attr)
        
        # Check if item is a class defined in this module
        if (isinstance(item, type) and 
            hasattr(item, '__module__') and 
            item.__module__ == mod.__name__):
            classes.append(item)
            
        # Recurse into submodules
        if isinstance(item, ModuleType):
            get_mod_classes(item, classes=classes, mod_path=mod_path, depth=depth+1)
    return classes

def get_addon_from_python_command(op_name):
    '''Get source addon from python command id_name
    param op_name : Operator idname or identifier (class name)
    Return a tuple containing module name and path to file
    '''

    import addon_utils
    from bpy.types import Operator
    from importlib import import_module
    import inspect

    op_name = op_name.strip()
    if op_name.startswith('bpy.ops.'):
        # op_name = op_name.replace('bpy.ops.', '').split('(')[0]
        op_name = op_name.split('.', 2)[-1].split('(')[0]
    
    for m in addon_utils.modules():
        name = m.__name__
        _default, loaded = addon_utils.check(name)
        if not loaded:
            continue
        mod = import_module(name)
        classes = get_mod_classes(mod)

        for c in classes:
            if (
                issubclass(c, Operator) 
                and  
                getattr(c, "bl_idname", "").startswith(op_name)
                ):
                print(name)
                return name, str(m).rsplit("'",1)[0].split("'")[-1]

        # for k in dir(mod):
        #     print(k)
        #     cls = getattr(mod, k, None)
        #     if inspect.isclass(cls) and issubclass(cls, Operator):
        #         id = getattr(cls, "bl_idname", "")
        #         if id.startswith(op_name):
        #             print(name)
        #             return name, 

def open_addon_prefs_by_name(name='', module=''):
    '''Open addon prefs windows with focus on current addon'''
    if not name:
        print('error: in open_addon_prefs_by_name : No name specified')
        return
    # from .__init__ import bl_info
    wm = bpy.context.window_manager
    wm.addon_filter = 'All'
    if not 'COMMUNITY' in  wm.addon_support: # reactivate community
        wm.addon_support = set([i for i in wm.addon_support] + ['COMMUNITY'])
    wm.addon_search = name
    bpy.context.preferences.active_section = 'ADDONS'
    if module:
        bpy.ops.preferences.addon_expand(module=module)
    bpy.ops.screen.userpref_show('INVOKE_DEFAULT')

## confirm pop-up message
def show_message_box(_message = "", _title = "Message Box", _icon = 'INFO'):
    '''Show message box with element passed as string or list
    if _message if a list of lists:
        if sublist have 2 element:
            considered a label [text, icon]
        if sublist have 3 element:
            considered as an operator [ops_id_name, text, icon]
        if sublist have 4 element:
            considered as a property [object, propname, text, icon]
    '''

    def draw(self, context):
        layout = self.layout
        for l in _message:
            if isinstance(l, str):
                layout.label(text=l)
            elif len(l) == 2: # label with icon
                layout.label(text=l[0], icon=l[1])
            elif len(l) == 3: # ops
                layout.operator_context = "INVOKE_DEFAULT"
                layout.operator(l[0], text=l[1], icon=l[2], emboss=False) # <- highligh the entry
            elif len(l) == 4: # prop
                row = layout.row(align=True)
                row.label(text=l[2], icon=l[3])
                row.prop(l[0], l[1], text='') 
    
    if isinstance(_message, str):
        _message = [_message]
    bpy.context.window_manager.popup_menu(draw, title = _title, icon = _icon)


def missing_external_editor():
    mess = 'External editor command or path should be specified in DevTools addon preferences'
    show_message_box(
        _message=[mess,
                'Since 4.0.0, you can set editor in preferences > filepath > text editor',
                ['dev.open_devtools_prefs', 'Open Preferences', 'PREFERENCES'],
                ],
        _title='No External editor')
    return mess

def console_write_and_execute_multiline(content, clear_line=True, skip_empty_line=True, context=None):
    '''Content can be either a string or a list of strings'''

    context = context or bpy.context
    if context.area.type != 'CONSOLE':
        print('/!\ console_write_and_execute_multiline not executed in a CONSOLE area')
        return
    
    if isinstance(content, str):
        # get a list of \n
        content = content.split('\n') 

    if clear_line and context.area.spaces.active.history[-1].body:
        # clear line if there is text already
        bpy.ops.console.clear_line()

    for lines in content:
        # split on returns
        for line in lines.split('\n'):
            if skip_empty_line and not line.strip():
                continue
            bpy.ops.console.insert(text=line)
            bpy.ops.console.execute()
