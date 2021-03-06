#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Benoit Chesneau <benoitc@e-engura.org>
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution.
#

import os
import re

from couchapp.couchapp_ext.compress import compress_css

class Compress(object):
    
    def __init__(self, ui, app_dir):
        self.ui = ui
        self.app_dir = app_dir
        self.attach_dir = self.ui.rjoin(app_dir, '_attachments')
        
    def is_hook(self):
        hooks = self.ui.conf['hooks']['pre-push']
        if not hooks.get('compress'):
            return False
        return True
        
    def compress_css(self, css):
        re_url = re.compile('url\s*\(([^\s"].*)\)')

        src_fpath = ''
        fname_dir = ''

        def replace_url(mo):
            """ make sure urls are relative to css path """
            css_url = mo.group(0)[4:].strip(")").replace("'", "").replace('"','')
            css_path = self.ui.rjoin(self.ui.dirname(src_fpath),
                    css_url)

            rel_path = _relpath(css_path, fname_dir)
            return "url(%s)" % rel_path

        for fname, src_files in css.iteritems():
            output_css = ''

            dest_path = self.ui.rjoin(self.attach_dir, fname)
            fname_dir = self.ui.dirname(dest_path)

            for src_fname in src_files:
                src_fpath = self.ui.rjoin(self.app_dir, src_fname)

                if self.ui.exists(src_fpath):
                    content_css = str(compress_css.CSSParser(self.ui.read(src_fpath)))
                    content_css = re_url.sub(replace_url, content_css)
                    output_css += content_css
                    if self.ui.verbose >= 2:
                        self.ui.logger.info("Merging %s in %s" % (src_fname, fname))

            if not self.ui.isdir(fname_dir):
                self.ui.makedirs(fname_dir)
            self.ui.write(dest_path, output_css)
            
    def compress_js(self, backend, js):
        if self.ui.verbose:
            self.ui.logger.info("compress js with %s " % backend.__about__)

        for fname, src_files in js.iteritems():
            output_js = ''

            dest_path = self.ui.rjoin(self.attach_dir, fname)
            fname_dir = self.ui.dirname(dest_path)

            for src_fname in src_files:
                src_fpath = self.ui.rjoin(self.app_dir, src_fname)
                if os.path.isfile(src_fpath):
                    output_js += "/* %s */\n" % src_fpath
                    output_js +=  self.ui.read(src_fpath)
                    if self.ui.verbose >= 2:
                        self.ui.logger.info("merging %s in %s" % (src_fname, fname))

            if not self.ui.isdir(fname_dir):
                self.ui.makedirs(fname_dir)

            output_js = backend.compress(output_js)
            self.ui.write(dest_path, output_js)
        
    def run(self):
        conf = self.ui.conf
        actions = conf['hooks']['pre-push']['compress']
        if 'css' in actions:
            self.compress_css(actions['css'])
        
        if 'js' in actions:
            if 'js_compressor' in conf['extensions']['compress']:
                modname = conf['extensions']['compress']['js_compressor']
                if not isinstance(modname, basestring):
                    self.ui.log.warning("Warning: js_compressor settings should be a string")
                    self.ui.log.warning("Selecting default backend (jsmin)")
                    import couchapp.couchapp_ext.compress.jsmin as backend
                else:
                    try:
                        backend = __import__(modname, {}, {}, [''])
                    except ImportError:
                         import couchapp.couchapp_ext.compress.jsmin as backend
            else:
                 import couchapp.couchapp_ext.compress.jsmin as backend
            self.compress_js(backend, actions['js'])
        

def hook(ui, app, hooktype, **kwargs):
    c = Compress(ui, app.app_dir)
        
    if hooktype == "pre-push":
        if not c.is_hook(): return
        c.run()
    