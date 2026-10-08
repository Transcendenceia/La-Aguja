import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import i18n
import profile as aguja_profile


class I18nTests(unittest.TestCase):
    def test_shared_selection_and_injection(self):
        for language in i18n.LANGUAGES:
            for keyboard, variants in i18n.KEYBOARD_VARIANTS.items():
                for variant in variants:
                    value=dict(language=language, keyboard=keyboard, variant=variant)
                    self.assertEqual(aguja_profile.validate_locale(value),value)
        for keyboard in ('cn;id', 'us\nBAD=yes', '$(touch /tmp/nope)'):
            with self.assertRaises(ValueError):
                aguja_profile.validate_locale(dict(language='zh_CN.UTF-8', keyboard=keyboard, variant=''))
        with self.assertRaises(ValueError):
            aguja_profile.validate_locale(dict(language='zh_CN.UTF-8', keyboard='cn', variant='intl'))

    def test_translation_placeholders_and_brand(self):
        for language in i18n.CATALOG['translations']:
            self.assertEqual(i18n.t('LA AGUJA',language=language),'LA AGUJA')
            source='Acceso del agente guardado en {path}; contiene URL y token privados y caduca en 24 horas.'
            value=i18n.t(source,language=language,path='/private/SYNTHETIC-URL-TOKEN.json')
            self.assertIn('/private/SYNTHETIC-URL-TOKEN.json',value)
            self.assertNotIn('{path}',value)
        self.assertEqual(i18n.t('Acceso remoto',language='zh_CN.UTF-8'),'远程访问')

    def test_owner_locale_overrides_forwarded_locale_and_refreshes(self):
        i18n._system_language.cache_clear()
        with patch('i18n.Path.read_text',return_value='LANG=zh_CN.UTF-8\n'), patch.dict(os.environ,{'LANG':'es_ES.UTF-8','LC_ALL':'en_US.UTF-8'}):
            self.assertEqual(i18n.ui_language(),'zh')
        i18n._system_language.cache_clear()
        with patch('i18n.Path.read_text',return_value='LANG=es_CO.UTF-8\n'):
            self.assertEqual(i18n.ui_language(),'es')
        i18n._system_language.cache_clear()

    def test_every_runtime_translated_literal_has_dictionary_coverage(self):
        for filename in ('display.py','cockpit.py'):
            tree=ast.parse((Path(i18n.__file__).parent / filename).read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='t' and node.args and isinstance(node.args[0],ast.Constant):
                    for language,entries in i18n.CATALOG['translations'].items():
                        self.assertIn(node.args[0].value,entries,(filename,language,node.args[0].value))

    def test_monitor_metadata_translates_but_raw_output_and_labels_do_not(self):
        with patch('i18n.ui_language',return_value='zh'):
            self.assertEqual(i18n.result_text('Completado'),'已完成')
            self.assertNotIn('SSH finalizado',i18n.event_text({'kind':'session_end','text':'SSH finalizado · Completado'}))
            self.assertEqual(i18n.event_text({'kind':'output','text':'Completado SSH finalizado'}),'Completado SSH finalizado')
            self.assertEqual(i18n.result_text('USER-LABEL-UNTRANSLATED'),'USER-LABEL-UNTRANSLATED')

    def test_cjk_font_requested_for_chinese_and_output_is_readable(self):
        import display
        from PIL import ImageFont
        # Verify real CJK font route without relying on host having build fonts.
        with patch('display.ui_language',return_value='zh'),patch('PIL.ImageFont.truetype',return_value='CJK-FONT') as truetype:
            display._font.cache_clear()
            self.assertEqual(display.font(20),'CJK-FONT')
            self.assertIn('NotoSansCJK-Regular.ttc',truetype.call_args.args[0])
            self.assertEqual(truetype.call_args.kwargs['index'],2)
        display._font.cache_clear()


if __name__=='__main__':unittest.main()
