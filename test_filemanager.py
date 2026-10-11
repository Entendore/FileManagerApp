import os
import shutil
import hashlib
import zipfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta          # ← FIX 2: added imports
from unittest.mock import patch, MagicMock

# Ensure Kivy doesn't try to load audio/video backends that might crash headless
os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'

from app import (
    _fmt_size, _fmt_date, _icon, _category, _type_name, _cat_color,
    _calc_hash, _folder_size, _folder_count, FileManager, DARK, LIGHT
)


# ═══════════════════════════════════════════════════════════════
#  FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def temp_fs(tmp_path):
    """Creates a temporary directory structure for testing."""
    # Folders
    (tmp_path / "folder1").mkdir()
    (tmp_path / "folder2").mkdir()
    (tmp_path / ".hidden_folder").mkdir()
    
    # Files
    (tmp_path / "folder1" / "file1.txt").write_text("Hello World", encoding="utf-8")
    (tmp_path / "folder1" / ".hidden_file").write_text("Secret", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"fake_png_data")
    (tmp_path / "script.py").write_text("print('hi')", encoding="utf-8")
    (tmp_path / "archive.zip").write_bytes(b"fake_zip_data")
    
    # Create a real zip for extraction tests
    zip_path = str(tmp_path / "real_archive.zip")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("zipped_text.txt", "Zipped Content")
        
    return tmp_path


@pytest.fixture
def fm(temp_fs):
    """Instantiates the FileManager with a mocked Kivy Window to allow headless testing."""
    # ── FIX 1: accept variable args since schedule_once can be called
    #    with just (callback,) or (callback, timeout) ──
    def _run_callback(f, *args, **kwargs):
        f(None)

    with patch('app.Window') as mock_window, \
         patch('app.Clock.schedule_once', side_effect=_run_callback):
        
        # Mock Window properties used by FileManager
        mock_window._modifiers = []
        mock_window.width = 1200
        mock_window.height = 800
        mock_window.clearcolor = [0, 0, 0, 1]
        mock_window.bind = MagicMock()          # prevent real Window binding
        
        manager = FileManager()
        manager._navigate(str(temp_fs))
        
        yield manager


# ═══════════════════════════════════════════════════════════════
#  UTILITY FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════

class TestUtilities:
    
    @pytest.mark.parametrize("size, expected", [
        (None, "—"), (-1, "—"), (0, "0 B"), 
        (512, "512 B"), (1024, "1.0 KB"), (1048576, "1.0 MB"), 
        (1073741824, "1.0 GB"), (1099511627776, "1.0 TB")
    ])
    def test_fmt_size(self, size, expected):
        assert _fmt_size(size) == expected

    def test_fmt_date_today(self):
        now = datetime.now().timestamp()
        assert "Today" in _fmt_date(now)

    def test_fmt_date_yesterday(self):
        yesterday = (datetime.now() - timedelta(days=1)).timestamp()
        assert "Yesterday" in _fmt_date(yesterday)

    def test_fmt_date_old(self):
        old = datetime(2020, 1, 1).timestamp()
        assert "2020-01-01" in _fmt_date(old)

    def test_fmt_date_error(self):
        assert _fmt_date("not_a_timestamp") == "—"

    @pytest.mark.parametrize("filename, is_dir, expected_cat", [
        ("test", True, "folder"),
        ("photo.jpg", False, "image"),
        ("song.mp3", False, "audio"),
        ("movie.mp4", False, "video"),
        ("main.py", False, "code"),
        ("report.pdf", False, "document"),
        ("data.json", False, "data"),
        ("archive.zip", False, "archive"),
        ("game.exe", False, "executable"),
        ("notes.txt", False, "text"),
        ("unknown.xyz", False, "other"),
    ])
    def test_categories_and_icons(self, filename, is_dir, expected_cat):
        assert _category(filename, is_dir) == expected_cat
        icon = _icon(filename, is_dir)
        assert isinstance(icon, str) and len(icon) > 0
        color = _cat_color(filename, is_dir)
        assert len(color) == 4  # RGBA

    def test_type_name(self):
        assert _type_name("my_folder", True) == "Folder"
        # ── FIX 3: "PY Source Code".upper() == "PY SOURCE CODE",
        #    it does NOT contain "PYTHON" ──
        result = _type_name("script.py", False)
        assert result == "PY Source Code"

    def test_calc_hash(self, tmp_path):
        file = tmp_path / "hash_test.txt"
        file.write_text("test content", encoding="utf-8")
        
        md5 = _calc_hash(str(file), "md5")
        sha = _calc_hash(str(file), "sha256")
        
        assert md5 == hashlib.md5(b"test content").hexdigest()
        assert sha == hashlib.sha256(b"test content").hexdigest()
        assert _calc_hash("non_existent_file.xyz", "md5") == "Error"

    def test_folder_size_and_count(self, temp_fs):
        path = str(temp_fs / "folder1")
        assert _folder_size(path) > 0
        assert _folder_count(path) == 2  # file1.txt, .hidden_file
        assert _folder_count("non_existent_dir_xyz") == -1


# ═══════════════════════════════════════════════════════════════
#  NAVIGATION & TABS TESTS
# ═══════════════════════════════════════════════════════════════

class TestNavigation:

    def test_initial_navigation(self, fm, temp_fs):
        assert fm.current_path == str(temp_fs)
        assert fm.path_input.text == str(temp_fs)

    def test_navigate_into_directory(self, fm, temp_fs):
        target = str(temp_fs / "folder1")
        fm._navigate(target)
        assert fm.current_path == target

    def test_navigate_invalid_directory(self, fm):
        with patch.object(fm, '_show_msg'):
            fm._navigate("/some/fake/path")
        assert "fake" not in fm.current_path

    def test_go_up(self, fm, temp_fs):
        fm._navigate(str(temp_fs / "folder1"))
        fm.go_up()
        assert fm.current_path == str(temp_fs)

    def test_go_back_and_forward(self, fm, temp_fs):
        start = str(temp_fs)
        target = str(temp_fs / "folder1")
        
        fm._navigate(target)
        assert fm.current_path == target
        
        fm.go_back()
        assert fm.current_path == start
        
        fm.go_forward()
        assert fm.current_path == target

    def test_add_and_switch_tabs(self, fm, temp_fs):
        assert len(fm.tabs) == 1
        fm._add_tab()
        assert len(fm.tabs) == 2
        assert fm.active_tab == 1
        
        fm._switch_tab(0)
        assert fm.active_tab == 0

    def test_close_tab(self, fm):
        fm._add_tab()
        fm._add_tab()
        assert len(fm.tabs) == 3
        
        fm._close_tab(2)
        assert len(fm.tabs) == 2
        
        fm._close_tab(fm.active_tab)
        assert len(fm.tabs) == 1


# ═══════════════════════════════════════════════════════════════
#  LISTING, SORTING & FILTERING TESTS
# ═══════════════════════════════════════════════════════════════

class TestListing:

    def test_list_dir_hides_files(self, fm):
        fm.show_hidden = False
        fm._list_dir()
        names = [w.display_name for w in fm.file_container.children]
        assert ".hidden_folder" not in names
        assert ".hidden_file" not in names

    def test_list_dir_shows_hidden(self, fm):
        fm.show_hidden = True
        fm._list_dir()
        names = [w.display_name for w in fm.file_container.children]
        assert ".hidden_folder" in names

    def test_search_filter(self, fm):
        fm.search_input.text = "image"
        fm._list_dir()
        names = [w.display_name for w in fm.file_container.children]
        assert "image.png" in names
        assert "script.py" not in names
        fm.search_input.text = ""

    def test_sort_by_name(self, fm):
        fm.sort_key = "name"
        fm.sort_rev = False
        fm._list_dir()
        items = [w.display_name for w in fm.file_container.children
                 if hasattr(w, 'filepath')]
        folders = [i for i in items
                   if os.path.isdir(os.path.join(fm.current_path, i))]
        assert len(folders) > 0

    def test_toggle_view_mode(self, fm):
        fm._toggle_view()
        assert fm.view_mode == "grid"
        fm._toggle_view()
        assert fm.view_mode == "list"


# ═══════════════════════════════════════════════════════════════
#  SELECTION TESTS
# ═══════════════════════════════════════════════════════════════

class TestSelection:

    def test_select_item_exclusive(self, fm, temp_fs):
        p1 = str(temp_fs / "image.png")
        p2 = str(temp_fs / "script.py")
        
        fm._select_item(p1, exclusive=True)
        assert fm.selected == [p1]
        
        fm._select_item(p2, exclusive=True)
        assert fm.selected == [p2]

    def test_select_item_additive(self, fm, temp_fs):
        p1 = str(temp_fs / "image.png")
        p2 = str(temp_fs / "script.py")
        
        fm._select_item(p1, exclusive=False)
        fm._select_item(p2, exclusive=False)
        
        assert p1 in fm.selected and p2 in fm.selected

    def test_select_all(self, fm):
        fm.select_all()
        assert len(fm.selected) > 0

    def test_invert_selection(self, fm, temp_fs):
        p1 = str(temp_fs / "image.png")
        fm._select_item(p1, exclusive=True)
        
        fm.invert_selection()
        assert p1 not in fm.selected


# ═══════════════════════════════════════════════════════════════
#  CLIPBOARD & FILE OPERATIONS TESTS
# ═══════════════════════════════════════════════════════════════

class TestFileOperations:

    def test_new_folder(self, fm, temp_fs):
        fm._create_item("new_dir", is_dir=True)
        assert (temp_fs / "new_dir").is_dir()

    def test_new_file(self, fm, temp_fs):
        fm._create_item("new_file.txt", is_dir=False)
        assert (temp_fs / "new_file.txt").is_file()

    def test_rename(self, fm, temp_fs):
        old = str(temp_fs / "script.py")
        fm.selected = [old]
        fm._do_rename(old, "renamed_script.py")
        
        assert not os.path.exists(old)
        assert (temp_fs / "renamed_script.py").is_file()
        assert fm.selected == [str(temp_fs / "renamed_script.py")]

    def test_copy_and_paste(self, fm, temp_fs):
        src = str(temp_fs / "image.png")
        fm.selected = [src]
        fm.copy_sel()
        
        assert fm.clipboard_mode == "copy"
        
        fm._navigate(str(temp_fs / "folder1"))
        fm._do_paste(str(temp_fs / "folder1"), overwrite=False)
        
        assert (temp_fs / "folder1" / "image.png").is_file()
        assert os.path.exists(src)

    def test_cut_and_paste(self, fm, temp_fs):
        src = str(temp_fs / "script.py")
        fm.selected = [src]
        fm.cut_sel()
        
        assert fm.clipboard_mode == "cut"
        
        fm._navigate(str(temp_fs / "folder1"))
        fm._do_paste(str(temp_fs / "folder1"), overwrite=False)
        
        assert (temp_fs / "folder1" / "script.py").is_file()
        assert not os.path.exists(src)

    def test_delete(self, fm, temp_fs):
        target = str(temp_fs / "image.png")
        fm.selected = [target]
        fm._do_delete()
        
        assert not os.path.exists(target)

    def test_zip_and_unzip(self, fm, temp_fs):
        src = str(temp_fs / "image.png")
        fm.selected = [src]
        fm._do_zip("images.zip")
        
        zip_path = temp_fs / "images.zip"
        assert zip_path.is_file()
        
        fm.selected = [str(zip_path)]
        fm._extract_zip(str(zip_path), str(temp_fs / "folder2"))
        assert (temp_fs / "folder2" / "image.png").is_file()

    def test_paste_conflict_skip(self, fm, temp_fs):
        src = str(temp_fs / "folder1" / "file1.txt")
        fm.selected = [src]
        fm.copy_sel()
        
        fm._do_paste(str(temp_fs), overwrite=False)
        assert (temp_fs / "file1.txt").is_file()
        
        fm._do_paste(str(temp_fs), overwrite=False)
        assert (temp_fs / "file1.txt").is_file()


# ═══════════════════════════════════════════════════════════════
#  UI TOGGLES & SETTINGS TESTS
# ═══════════════════════════════════════════════════════════════

class TestToggles:

    def test_toggle_hidden(self, fm):
        initial = fm.show_hidden
        fm._toggle_hidden()
        assert fm.show_hidden != initial

    def test_toggle_preview(self, fm):
        initial = fm.show_preview
        fm._toggle_preview()
        assert fm.show_preview != initial

    def test_toggle_theme(self, fm):
        assert fm._dark_mode is True
        
        fm._toggle_theme()
        assert fm._dark_mode is False
        
        fm._toggle_theme()
        assert fm._dark_mode is True

    def test_toggle_bookmark(self, fm):
        path = fm.current_path
        fm.toggle_bookmark()
        assert path in fm.bookmarks
        
        fm.toggle_bookmark()
        assert path not in fm.bookmarks


# ═══════════════════════════════════════════════════════════════
#  CONTEXT MENU & PROPERTIES TESTS
# ═══════════════════════════════════════════════════════════════

class TestContextAndProperties:

    def test_show_properties(self, fm, temp_fs):
        target = str(temp_fs / "image.png")
        fm.selected = [target]
        
        with patch.object(fm, '_show_msg') as mock_msg:
            fm._show_properties(target)
            mock_msg.assert_called_once()
            assert "image.png" in mock_msg.call_args[0][0]

    def test_context_menu_instantiation(self):
        items = [("Test Item", lambda: None)]
        with patch('app.Window', width=800, height=600):
            from app import ContextMenu
            menu = ContextMenu(items, (100, 100))
            assert menu.size[0] > 0
            assert menu.size[1] > 0