"""Seletor de pastas independente; no Windows, usa o próprio Explorer.

O Common Item Dialog dispensa Tcl/Tk e pacotes Python adicionais no Windows.
Contrato nativo: https://learn.microsoft.com/windows/win32/shell/common-file-dialog
"""
from pathlib import Path
import ctypes
import json
import sys
import uuid

DESKTOP_MESSAGE = ('Para abrir a janela de pastas na sua tela, abra a bancada '
                   'com dois cliques em Abrir_bancada.cmd e tente novamente.')


def interactive_desktop():
    """Uma janela não deve ser criada numa área isolada ou sem desktop visível."""
    if sys.platform != 'win32':
        return True
    from ctypes import wintypes

    user = ctypes.WinDLL('user32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32')
    kernel.GetCurrentThreadId.argtypes = []
    kernel.GetCurrentThreadId.restype = wintypes.DWORD
    user.GetThreadDesktop.argtypes = [wintypes.DWORD]
    user.GetThreadDesktop.restype = wintypes.HANDLE
    user.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user.OpenInputDesktop.restype = wintypes.HANDLE
    user.CloseDesktop.argtypes = [wintypes.HANDLE]
    user.CloseDesktop.restype = wintypes.BOOL
    user.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int,
        ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    user.GetUserObjectInformationW.restype = wintypes.BOOL

    def name(handle):
        value = ctypes.create_unicode_buffer(256)
        needed = wintypes.DWORD()
        if not handle or not user.GetUserObjectInformationW(
                handle, 2, value, ctypes.sizeof(value), ctypes.byref(needed)):
            return None
        return value.value

    visible = user.OpenInputDesktop(0, False, 0x0001)  # DESKTOP_READOBJECTS.
    if not visible:
        return False
    try:
        current_name = name(user.GetThreadDesktop(kernel.GetCurrentThreadId()))
        return bool(current_name and current_name == name(visible))
    finally:
        user.CloseDesktop(visible)


class GUID(ctypes.Structure):
    _fields_ = [('data1', ctypes.c_uint32), ('data2', ctypes.c_uint16),
                ('data3', ctypes.c_uint16), ('data4', ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


def check_hresult(value, operation):
    if value & 0x80000000:
        raise RuntimeError(f'{operation}: erro do Windows 0x{value & 0xffffffff:08X}.')


def dialog_result(folder):
    if not folder:
        return {'cancelled': True, 'folder': None}
    path = Path(folder).resolve()
    if not path.is_dir():
        raise ValueError('A pasta escolhida não está disponível.')
    return {'cancelled': False, 'folder': str(path)}


def choose_windows(initial=''):
    """Abre IFileOpenDialog em modo pasta, no processo auxiliar STA."""
    if not interactive_desktop():
        raise RuntimeError(DESKTOP_MESSAGE)
    from ctypes import wintypes

    pointer = ctypes.c_void_p
    hresult = ctypes.c_long
    ole = ctypes.WinDLL('ole32')
    shell = ctypes.WinDLL('shell32')
    ole.CoInitializeEx.argtypes = [pointer, wintypes.DWORD]
    ole.CoInitializeEx.restype = hresult
    ole.CoUninitialize.argtypes = []
    ole.CoUninitialize.restype = None
    ole.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), pointer, wintypes.DWORD,
                                    ctypes.POINTER(GUID), ctypes.POINTER(pointer)]
    ole.CoCreateInstance.restype = hresult
    ole.CoTaskMemFree.argtypes = [pointer]
    ole.CoTaskMemFree.restype = None
    shell.SHCreateItemFromParsingName.argtypes = [wintypes.LPCWSTR, pointer,
                                                ctypes.POINTER(GUID), ctypes.POINTER(pointer)]
    shell.SHCreateItemFromParsingName.restype = hresult

    # Índices das interfaces COM do Windows SDK: IUnknown, IModalWindow,
    # IFileDialog e IShellItem. WINFUNCTYPE preserva a convenção de chamada.
    def method(obj, index, result_type, *argument_types):
        table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(pointer))).contents
        return ctypes.WINFUNCTYPE(result_type, pointer, *argument_types)(table[index])

    def release(obj):
        if obj:
            method(obj, 2, wintypes.ULONG)(obj)

    clsid = GUID.parse('DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7')
    iid_dialog = GUID.parse('D57C7288-D4AD-4768-BE02-9D969532D960')
    iid_item = GUID.parse('43826D1E-E718-42EE-BC55-A1E261C37BFE')
    dialog, start_item, result_item, path_buffer = pointer(), pointer(), pointer(), pointer()
    # COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE.
    check_hresult(ole.CoInitializeEx(None, 0x2 | 0x4), 'Inicializar seletor')
    try:
        check_hresult(ole.CoCreateInstance(ctypes.byref(clsid), None, 1,
                                           ctypes.byref(iid_dialog), ctypes.byref(dialog)),
                      'Criar seletor de pastas')
        options = wintypes.DWORD()
        check_hresult(method(dialog, 10, hresult, ctypes.POINTER(wintypes.DWORD))(
            dialog, ctypes.byref(options)), 'Ler opções do seletor')
        # PICKFOLDERS | FORCEFILESYSTEM | PATHMUSTEXIST | NOCHANGEDIR | DONTADDTORECENT.
        flags = options.value | 0x20 | 0x40 | 0x800 | 0x8 | 0x02000000
        check_hresult(method(dialog, 9, hresult, wintypes.DWORD)(dialog, flags),
                      'Configurar seletor de pastas')
        check_hresult(method(dialog, 17, hresult, wintypes.LPCWSTR)(
            dialog, 'Escolha a pasta de imagens'), 'Definir título')
        check_hresult(method(dialog, 18, hresult, wintypes.LPCWSTR)(
            dialog, 'Selecionar pasta'), 'Definir botão')

        if initial and Path(initial).is_dir():
            # Reabrir na pasta em uso permite mudar de conjunto conscientemente.
            status = shell.SHCreateItemFromParsingName(str(Path(initial).resolve()), None,
                ctypes.byref(iid_item), ctypes.byref(start_item))
            if not status & 0x80000000:
                method(dialog, 12, hresult, pointer)(dialog, start_item)

        status = method(dialog, 3, hresult, wintypes.HWND)(dialog, None)
        if status & 0xffffffff == 0x800704C7:  # ERROR_CANCELLED, não é falha.
            return dialog_result(None)
        check_hresult(status, 'Abrir seletor de pastas')
        check_hresult(method(dialog, 20, hresult, ctypes.POINTER(pointer))(
            dialog, ctypes.byref(result_item)), 'Obter pasta selecionada')
        # SIGDN_FILESYSPATH devolve Unicode; a memória pertence ao alocador COM.
        check_hresult(method(result_item, 5, hresult, wintypes.DWORD, ctypes.POINTER(pointer))(
            result_item, 0x80058000, ctypes.byref(path_buffer)), 'Ler caminho da pasta')
        return dialog_result(ctypes.wstring_at(path_buffer))
    finally:
        if path_buffer:
            ole.CoTaskMemFree(path_buffer)
        release(result_item)
        release(start_item)
        release(dialog)
        ole.CoUninitialize()


def choose_tk(initial=''):
    # Importação tardia: um Tcl/Tk ausente não impede o seletor do Windows.
    import tkinter as tk
    from tkinter import filedialog

    root=tk.Tk()
    root.withdraw()
    root.attributes('-topmost',True)
    try:
        options={'parent':root,'title':'Escolha a pasta de imagens','mustexist':True}
        if initial and Path(initial).is_dir(): options['initialdir']=str(Path(initial))
        folder=filedialog.askdirectory(**options)
        return dialog_result(folder)
    finally: root.destroy()


def choose(initial=''):
    return choose_windows(initial) if sys.platform == 'win32' else choose_tk(initial)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(choose(sys.argv[1] if len(sys.argv)>1 else ''),ensure_ascii=False))
