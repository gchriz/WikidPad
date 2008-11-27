import re

import wx, wx.xrc

from wxHelper import *

from StringOps import uniToGui, guiToUni, htmlColorToRgbTuple,\
        rgbToHtmlColor, strToBool

from AdditionalDialogs import DateformatDialog, FontFaceDialog

import Configuration
import Localization

import WikiHtmlView



class DefaultOptionsPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

    def setVisible(self, vis):
        return True

    def checkOk(self):
        return True

    def handleOk(self):
        pass


class ResourceOptionsPanel(DefaultOptionsPanel):
    """
    GUI of panel is defined by a ressource.
    """
    def __init__(self, parent, resName):
        p = wx.PrePanel()
        self.PostCreate(p)
#         self.optionsDlg = optionsDlg
        res = wx.xrc.XmlResource.Get()
        
        res.LoadOnPanel(self, parent, resName)
        
    def setVisible(self, vis):
        return True

    def checkOk(self):
        return True

    def handleOk(self):
        pass


class PluginOptionsPanel(DefaultOptionsPanel):
    def __init__(self, parent, optionsDlg, app):
        DefaultOptionsPanel.__init__(self, parent)

        self.idToOptionEntryMap = {}
        self.oldSettings = {}
        self.optionToControl = []
        self.mainControl = optionsDlg.getMainControl()

    
    def addOptionEntry(self, opt, ctl, typ, *params):
        self.optionToControl.append((opt, ctl, typ) + params)
    
    
    def transferOptionsToDialog(self, config):
        # List of tuples (<configuration file entry>, <gui control name>, <type>)
        # Supported types:
        #     b: boolean checkbox
        #     i0+: nonnegative integer
        #     t: text
        #     tre: regular expression
        #     ttdf: time/date format
        #     f0+: nonegative float
        #     seli: integer position of a selection in dropdown list
        #     selt: Chosen text in dropdown list
        #     color0: HTML color code or empty
        #     spin: Numeric SpinCtrl
        #
        #     guilang: special choice for GUI language
    
        # ttdf and color0 entries have a 4th item with the name
        #     of the "..." button to call a dialog to set.
        # selt entries have a list with the internal config names (unicode) of the
        #     possible choices as 4th item.

        # Transfer options to dialog
        for oct in self.optionToControl:
            self.transferSingleOptionToDialog(config, oct)


    def transferSingleOptionToDialog(self, config, oct):
        o, ctl, t = oct[:3]
        self.idToOptionEntryMap[ctl.GetId()] = oct
        self.oldSettings[o] = config.get("main", o)

        if t == "b":   # boolean field = checkbox
            ctl.SetValue(
                    config.getboolean("main", o))
        elif t == "b3":   # boolean field = checkbox
            value = config.get("main", o)
            if value == "Gray":
                ctl.Set3StateValue(wx.CHK_UNDETERMINED)
            else:
                if strToBool(value):
                    ctl.Set3StateValue(wx.CHK_CHECKED)
                else:
                    ctl.Set3StateValue(wx.CHK_UNCHECKED)

#                 ctl.SetValue(
#                         config.getboolean("main", o))
        elif t in ("t", "tre", "ttdf", "i0+", "f0+", "color0"):  # text field or regular expression field
            ctl.SetValue(
                    uniToGui(config.get("main", o)) )
        elif t == "seli":   # Selection -> transfer index
            ctl.SetSelection(config.getint("main", o))
        elif t == "selt":   # Selection -> transfer content string
            try:
                idx = oct[3].index(config.get("main", o))
                ctl.SetSelection(idx)
            except (IndexError, ValueError):
                ctl.SetStringSelection(uniToGui(config.get("main", o)) )
        elif t == "spin":   # Numeric SpinCtrl -> transfer number
            ctl.SetValue(config.getint("main", o))
        elif t == "guilang":   # GUI language choice
            # First fill choice with options
            ctl.Append(_(u"Default"))
            for ls, lt in Localization.getLangList():
                ctl.Append(lt)
            
            # Then select previous setting                
            optValue = config.get("main", o)
            ctl.SetSelection(Localization.findLangListIndex(optValue) + 1)


        # Register events for "..." buttons
        if t in ("color0", "ttdf"):
            params = oct[3:]
            if len(params) > 0:
                # params[0] is the "..." button after the text field
                dottedButtonId = params[0].GetId()
                self.idToOptionEntryMap[dottedButtonId] = oct

                wx.EVT_BUTTON(self, dottedButtonId,
                        self.OnDottedButtonPressed)


    def checkOk(self):
        """
        Called when "OK" is pressed in dialog. The plugin should check here if
        all input values are valid. If not, it should return False, then the
        Options dialog automatically shows this panel.
        
        There should be a visual indication about what is wrong (e.g. red
        background in text field). Be sure to reset the visual indication
        if field is valid again.
        """
        fieldsValid = True

        # First check validity of field contents
        for oct in self.optionToControl:
            if not self.checkSingleOptionOk(oct):
                fieldsValid = False
        
        return fieldsValid


    def checkSingleOptionOk(self, oct):
        o, ctl, t = oct[:3]
        fieldsValid = True

        if t == "tre":
            # Regular expression field, test if re is valid
            try:
                rexp = guiToUni(ctl.GetValue())
                re.compile(rexp, re.DOTALL | re.UNICODE | re.MULTILINE)
                ctl.SetBackgroundColour(wx.WHITE)
            except:   # TODO Specific exception
                fieldsValid = False
                ctl.SetBackgroundColour(wx.RED)
        elif t == "i0+":
            # Nonnegative integer field
            try:
                val = int(guiToUni(ctl.GetValue()))
                if val < 0:
                    raise ValueError
                ctl.SetBackgroundColour(wx.WHITE)
            except ValueError:
                fieldsValid = False
                ctl.SetBackgroundColour(wx.RED)
        elif t == "f0+":
            # Nonnegative float field
            try:
                val = float(guiToUni(ctl.GetValue()))
                if val < 0:
                    raise ValueError
                ctl.SetBackgroundColour(wx.WHITE)
            except ValueError:
                fieldsValid = False
                ctl.SetBackgroundColour(wx.RED)
        elif t == "color0":
            # HTML Color field or empty field
            val = guiToUni(ctl.GetValue())
            rgb = htmlColorToRgbTuple(val)
            
            if val != "" and rgb is None:
                ctl.SetBackgroundColour(wx.RED)
                fieldsValid = False
            else:
                ctl.SetBackgroundColour(wx.WHITE)
        elif t == "spin":
            # SpinCtrl
            try:
                val = ctl.GetValue()
                if val < ctl.GetMin() or \
                        val > ctl.GetMax():
                    raise ValueError
                ctl.SetBackgroundColour(wx.WHITE)
            except ValueError:
                fieldsValid = False
                ctl.SetBackgroundColour(wx.RED)

        return fieldsValid



    def transferDialogToOptions(self, config):
        for oct in self.optionToControl:
            self.transferDialogToSingleOption(config, oct)

    def transferDialogToSingleOption(self, config, oct):
        """
        Transfer option from dialog to config object
        """
        o, ctl, t = oct[:3]

        # TODO Handle unicode text controls
        if t == "b":
            config.set("main", o, repr(ctl.GetValue()))
        elif t == "b3":
            value = ctl.Get3StateValue()
            if value == wx.CHK_UNDETERMINED:
                config.set("main", o, "Gray")
            elif value == wx.CHK_CHECKED:
                config.set("main", o, "True")
            elif value == wx.CHK_UNCHECKED:
                config.set("main", o, "False")

        elif t in ("t", "tre", "ttdf", "i0+", "f0+", "color0"):
            config.set(
                    "main", o, guiToUni(ctl.GetValue()) )
        elif t == "seli":   # Selection -> transfer index
            config.set(
                    "main", o, unicode(ctl.GetSelection()) )
        elif t == "selt":   # Selection -> transfer content string
            try:
                config.set("main", o,
                        oct[3][ctl.GetSelection()])
            except IndexError:
                config.set("main", o, 
                        guiToUni(ctl.GetStringSelection()))
        elif t == "spin":   # Numeric SpinCtrl -> transfer number
            config.set(
                    "main", o, unicode(ctl.GetValue()) )
        elif t == "guilang":    # GUI language choice
            idx = ctl.GetSelection()
            if idx < 1:
                config.set("main", o, u"")
            else:
                config.set("main", o,
                        Localization.getLangList()[idx - 1][0])

    def OnDottedButtonPressed(self, evt):
        """
        Called when a "..." button is pressed (for some of them) to show
        an alternative way to specify the input, e.g. showing a color selector
        for color entries instead of using the bare text field
        """
        oct = self.idToOptionEntryMap[evt.GetId()]
        o, ctl, t = oct[:3]
        params = oct[3:]
        
        if t == "color0":
            self.selectColor(ctl)
        elif t == "ttdf":   # Date/time format
            self.selectDateTimeFormat(ctl)


    def selectColor(self, tfield):
        rgb = htmlColorToRgbTuple(tfield.GetValue())
        if rgb is None:
            rgb = (0, 0, 0)

        color = wx.Colour(*rgb)
        colordata = wx.ColourData()
        colordata.SetColour(color)

        dlg = wx.ColourDialog(self, colordata)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                color = dlg.GetColourData().GetColour()
                if color.Ok():
                    tfield.SetValue(
                            rgbToHtmlColor(color.Red(), color.Green(),
                            color.Blue()))
        finally:
            dlg.Destroy()

    def selectDateTimeFormat(self, tfield):
        dlg = DateformatDialog(self, -1, self.mainControl, 
                deffmt=tfield.GetValue())
        try:
            if dlg.ShowModal() == wx.ID_OK:
                tfield.SetValue(dlg.GetValue())
        finally:
            dlg.Destroy()



# class KeyDefField(wx.TextCtrl):
#     def __init__(self, parent, ID=-1):
#         wx.TextCtrl.__init__(self, parent, ID)
#         self.mods = None
#         self.vkCode = None
#         EVT_
#     def


class OptionsDialog(wx.Dialog):
    # List of tuples (<configuration file entry>, <gui control name>, <type>)
    # Supported types:
    #     b: boolean checkbox
    #     i0+: nonnegative integer
    #     t: text
    #     tre: regular expression
    #     ttdf: time/date format
    #     f0+: nonegative float
    #     seli: integer position of a selection in dropdown list
    #     selt: Chosen text in dropdown list
    #     color0: HTML color code or empty
    #     spin: Numeric SpinCtrl
    #
    #     guilang: special choice for GUI language

    # ttdf and color0 entries have a 4th item with the name
    #     of the "..." button to call a dialog to set.
    # selt entries have a list with the internal config names (unicode) of the
    #     possible choices as 4th item.

    OPTION_TO_CONTROL = (
            # application-wide options
            
            ("single_process", "cbSingleProcess", "b"),
            ("wikiPathes_relative", "cbWikiPathesRelative", "b"),
            ("wikiOpenNew_defaultDir", "tfWikiOpenNewDefaultDir",
                "t"),
            ("collation_order", "chCollationOrder", "selt",
                [u"Default", u"C"]),
            ("collation_uppercaseFirst", "cbCollationUppercaseFirst", "b"),
            ("wikiWord_rename_wikiLinks", "chWikiWordRenameWikiLinks", "seli"),
            ("hotKey_showHide_byApp_isActive", "cbHotKeyShowHideByAppIsActive",
                "b"),
            ("hotKey_showHide_byApp", "tfHotKeyShowHideByApp", "t"),


            ("showontray", "cbShowOnTray", "b"),
            ("minimize_on_closeButton", "cbMinimizeOnCloseButton", "b"),
            ("pagestatus_timeformat", "tfPageStatusTimeFormat", "ttdf",
                "btnSelectPageStatusTimeFormat"),
            ("gui_language", "chGuiLanguage", "guilang"),
            ("recentWikisList_length", "scRecentWikisListLength", "spin"),

            ("option/user/log_window_autoshow", "cbLogWindowAutoShowUser", "b"),
            ("log_window_autohide", "cbLogWindowAutoHide", "b"),
            ("docStructure_position", "chDocStructurePosition", "seli"),
            ("docStructure_depth", "scDocStructureDepth", "spin"),
            ("docStructure_autohide", "cbDocStructureAutoHide", "b"),


            ("process_autogenerated_areas", "cbProcessAutoGenerated", "b"),
            ("insertions_allow_eval", "cbInsertionsAllowEval", "b"),
#             ("tempFiles_inWikiDir", "cbTempFilesInWikiDir", "b"),
            ("script_security_level", "chScriptSecurityLevel", "seli"),


            ("mainTree_position", "chMainTreePosition", "seli"),
            ("viewsTree_position", "chViewsTreePosition", "seli"),
            ("tree_auto_follow", "cbTreeAutoFollow", "b"),
            ("tree_update_after_save", "cbTreeUpdateAfterSave", "b"),
            ("hideundefined", "cbHideUndefinedWords", "b"),
            ("tree_no_cycles", "cbTreeNoCycles", "b"),
            ("tree_autohide", "cbTreeAutoHide", "b"),
            ("tree_bg_color", "tfTreeBgColor", "color0",
                    "btnSelectTreeBgColor"),


            ("start_browser_after_export", "cbStartBrowserAfterExport", "b"),
            ("facename_html_preview", "tfFacenameHtmlPreview", "t"),
            ("html_preview_proppattern_is_excluding",
                    "cbHtmlPreviewProppatternIsExcluding", "b"),
            ("html_preview_proppattern", "tfHtmlPreviewProppattern", "tre"),
            ("html_export_proppattern_is_excluding",
                    "cbHtmlExportProppatternIsExcluding", "b"),
            ("html_export_proppattern", "tfHtmlExportProppattern", "tre"),
            ("html_preview_pics_as_links", "cbHtmlPreviewPicsAsLinks", "b"),
            ("html_export_pics_as_links", "cbHtmlExportPicsAsLinks", "b"),
            ("html_preview_renderer", "chHtmlPreviewRenderer", "seli"),
            ("export_table_of_contents", "chTableOfContents", "seli"),
            ("html_toc_title", "tfHtmlTocTitle", "t"),
            ("html_export_singlePage_sepLineCount",
                    "tfHtmlExportSinglePageSepLineCount", "i0+"),


            ("html_body_link", "tfHtmlLinkColor", "color0",
                "btnSelectHtmlLinkColor"),
            ("html_body_alink", "tfHtmlALinkColor", "color0",
                "btnSelectHtmlALinkColor"),
            ("html_body_vlink", "tfHtmlVLinkColor", "color0",
                "btnSelectHtmlVLinkColor"),
            ("html_body_text", "tfHtmlTextColor", "color0",
                "btnSelectHtmlTextColor"),
            ("html_body_bgcolor", "tfHtmlBgColor", "color0",
                "btnSelectHtmlBgColor"),
            ("html_body_background", "tfHtmlBgImage", "t"),
            ("html_header_doctype", "tfHtmlDocType", "t"),


            ("auto_save", "cbAutoSave", "b"),
            ("auto_save_delay_key_pressed", "tfAutoSaveDelayKeyPressed", "i0+"),
            ("auto_save_delay_dirty", "tfAutoSaveDelayDirty", "i0+"),


            ("sync_highlight_byte_limit", "tfSyncHighlightingByteLimit", "i0+"),
            ("async_highlight_delay", "tfAsyncHighlightingDelay", "f0+"),
            ("editor_shortHint_delay", "tfEditorShortHintDelay", "i0+"),
            ("editor_autoUnbullets", "cbAutoUnbullets", "b"),
            ("editor_autoComplete_closingBracket",
                "cbAutoCompleteClosingBracket", "b"),
            ("editor_sync_byPreviewSelection", "cbEditorSyncByPreviewSelection",
                "b"),

            ("editor_imagePaste_filenamePrefix", "tfEditorImagePasteFilenamePrefix", "t"),
            ("editor_imagePaste_fileType", "chEditorImagePasteFileType", "seli"),
            ("editor_imagePaste_quality", "tfEditorImagePasteQuality", "i0+"),
            ("editor_imagePaste_askOnEachPaste", "cbEditorImagePasteAskOnEachPaste", "b"),


            ("editor_plaintext_color", "tfEditorPlaintextColor", "color0",
                    "btnSelectEditorPlaintextColor"),
            ("editor_link_color", "tfEditorLinkColor", "color0",
                    "btnSelectEditorLinkColor"),
            ("editor_attribute_color", "tfEditorAttributeColor", "color0",
                    "btnSelectEditorAttributeColor"),
            ("editor_bg_color", "tfEditorBgColor", "color0",
                    "btnSelectEditorBgColor"),
            ("editor_selection_fg_color", "tfEditorSelectionFgColor", "color0",
                    "btnSelectEditorSelectionFgColor"),
            ("editor_selection_bg_color", "tfEditorSelectionBgColor", "color0",
                    "btnSelectEditorSelectionBgColor"),
            ("editor_margin_bg_color", "tfEditorMarginBgColor", "color0",
                    "btnSelectEditorMarginBgColor"),
            ("editor_caret_color", "tfEditorCaretColor", "color0",
                    "btnSelectEditorCaretColor"),


            ("mouse_middleButton_withoutCtrl", "chMouseMiddleButtonWithoutCtrl", "seli"),
            ("mouse_middleButton_withCtrl", "chMouseMiddleButtonWithCtrl", "seli"),
            ("userEvent_mouse/leftdoubleclick/preview/body", "chMouseDblClickPreviewBody", "selt",
                    [
                    u"action/none",
                    u"action/presenter/this/subcontrol/textedit",
                    u"action/presenter/new/foreground/end/page/this/subcontrol/textedit"
                    ]),
                
            ("userEvent_mouse/middleclick/pagetab", "chMouseMdlClickPageTab", "selt",
                    [
                    u"action/none",
                    u"action/presenter/this/close",
                    u"action/presenter/this/clone"
                    ]),

            ("userEvent_mouse/leftdrop/editor/files", "chMouseLeftDropEditor", "selt",
                    [
                    u"action/none",
                    u"action/editor/this/paste/files/insert/url/absolute",
                    u"action/editor/this/paste/files/insert/url/relative",
                    u"action/editor/this/paste/files/insert/url/tostorage"
                    ]),

            ("userEvent_mouse/leftdrop/editor/files/modkeys/shift", "chMouseLeftDropEditorShift", "selt",
                    [
                    u"action/none",
                    u"action/editor/this/paste/files/insert/url/absolute",
                    u"action/editor/this/paste/files/insert/url/relative",
                    u"action/editor/this/paste/files/insert/url/tostorage"
                    ]),

            ("userEvent_mouse/leftdrop/editor/files/modkeys/ctrl", "chMouseLeftDropEditorCtrl", "selt",
                    [
                    u"action/none",
                    u"action/editor/this/paste/files/insert/url/absolute",
                    u"action/editor/this/paste/files/insert/url/relative",
                    u"action/editor/this/paste/files/insert/url/tostorage"
                    ]),

            ("timeView_position", "chTimeViewPosition", "seli"),
            ("timeView_dateFormat", "tfTimeViewDateFormat", "ttdf",
                "btnSelectTimeViewDateFormat"),
            ("timeView_autohide", "cbTimeViewAutoHide", "b"),

            ("timeView_showWordListOnHovering",
                    "cbTimeViewShowWordListOnHovering", "b"),
            ("timeView_showWordListOnSelect",
                    "cbTimeViewShowWordListOnSelect", "b"),
            ("timeline_showEmptyDays", "cbTimelineShowEmptyDays", "b"),
            ("timeline_sortDateAscending", "cbTimelineSortDateAscending", "b"),


            ("search_wiki_context_before", "tfWwSearchContextBefore", "i0+"),
            ("search_wiki_context_after", "tfWwSearchContextAfter", "i0+"),
            ("search_wiki_count_occurrences", "cbWwSearchCountOccurrences", "b"),
            ("incSearch_autoOffDelay", "tfIncSearchAutoOffDelay", "i0+"),


            ("wikiLockFile_ignore", "cbWikiLockFileIgnore", "b"),
            ("wikiLockFile_create", "cbWikiLockFileCreate", "b"),


            # wiki-specific options

            ("footnotes_as_wikiwords", "cbFootnotesAsWws", "b"),
            ("first_wiki_word", "tfFirstWikiWord", "t"),

            ("wikiPageTitlePrefix", "tfWikiPageTitlePrefix", "t"),
            ("wikiPageTitle_creationMode", "chWikiPageTitleCreationMode", "seli"),
            ("wikiPageTitle_fromLinkTitle", "cbWikiPageTitleFromLinkTitle", "b"),

            ("export_default_dir", "tfExportDefaultDir", "t"),

            ("tree_expandedNodes_rememberDuration",
                    "chTreeExpandedNodesRememberDuration", "seli"),

            ("tree_force_scratchpad_visibility",
                    "cbTreeForceScratchpadVisibility", "b"),

            ("option/wiki/log_window_autoshow", "cbLogWindowAutoShowWiki", "b3"),

            ("wiki_icon", "tfWikiIcon", "t"),

            ("hotKey_showHide_byWiki", "tfHotKeyShowHideByWiki", "t"),


            ("fileStorage_identity_modDateMustMatch", "cbFsModDateMustMatch", "b"),
            ("fileStorage_identity_filenameMustMatch", "cbFsFilenameMustMatch", "b"),
            ("fileStorage_identity_modDateIsEnough", "cbFsModDateIsEnough", "b")
            
    )


    # Windows specific options
    OPTION_TO_CONTROL_WINDOWS_ONLY = (
            ("clipboardCatcher_prefix", "tfClipboardCatcherPrefix", "t"),
            ("clipboardCatcher_suffix", "tfClipboardCatcherSuffix", "t"),
            ("clipboardCatcher_filterDouble", "cbClipboardCatcherFilterDouble",
                    "b"),
            ("clipboardCatcher_userNotification", "chClipCatchUserNotification", "seli"),
            ("clipboardCatcher_soundFile", "tfClipCatchSoundFile", "t")
    )

    # Non-Windows specific options    
    OPTION_TO_CONTROL_NON_WINDOWS_ONLY = (
            ("fileLauncher_path", "tfFileLauncherPath", "t"),
    )
    


    DEFAULT_PANEL_LIST = (
            ("OptionsPageApplication", N_(u"Application")),    
            ("OptionsPageUserInterface", N_(u"  User interface")),
            ("OptionsPageSecurity", N_(u"  Security")),
            ("OptionsPageTree", N_(u"  Tree")),
            ("OptionsPageHtml", N_(u"  HTML preview/export")),
            ("OptionsPageHtmlHeader", N_(u"    HTML header")),
            ("OptionsPageAutosave", N_(u"  Autosave")),
            ("OptionsPageEditor", N_(u"  Editor")),
            ("OptionsPageEditorColors", N_(u"    Editor Colors")),
            ("OptionsPageClipboardCatcher", N_(u"    Clipboard Catcher")),
            ("OptionsPageFileLauncher", N_(u"  File Launcher")),
            ("OptionsPageMouse", N_(u"  Mouse")),
            ("OptionsPageTimeView", N_(u"  Time view")),
            ("OptionsPageSearching", N_(u"  Searching")),  
            ("OptionsPageAdvanced", N_(u"  Advanced")),  
            ("OptionsPageCurrentWiki", N_(u"Current Wiki")),
            ("OptionsPageCwFileStorage", N_(u"  File Storage"))
    )

    def __init__(self, pWiki, ID, title="Options",
                 pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=wx.NO_3D):
        d = wx.PreDialog()
        self.PostCreate(d)

        self.pWiki = pWiki
        self.oldSettings = {}
        res = wx.xrc.XmlResource.Get()
        res.LoadOnDialog(self, self.pWiki, "OptionsDialog")

        self.combinedOptionToControl = self.OPTION_TO_CONTROL
        self.combinedPanelList = wx.GetApp().getOptionsDlgPanelList()
        # Maps ids of the GUI controls named in self.combinedOptionToControl
        # to the entries (the appropriate tuple) there
        self.idToOptionEntryMap = {}

        if Configuration.isWindows():
            self.combinedOptionToControl += self.OPTION_TO_CONTROL_WINDOWS_ONLY

            newPL = []
            for e in self.combinedPanelList:
                if e[0] == "OptionsPageFileLauncher":
                    continue

                newPL.append(e)

            self.combinedPanelList = newPL
        else:
            self.combinedOptionToControl += self.OPTION_TO_CONTROL_NON_WINDOWS_ONLY

            newPL = []
            for i, e in enumerate(self.combinedPanelList):
                if e[0] == "OptionsPageClipboardCatcher":
                    continue

                newPL.append(e)

            self.combinedPanelList = newPL

        self.ctrls = XrcControls(self)

        self.emptyPanel = None

        self.panelList = []
        self.ctrls.lbPages.Clear()


        mainsizer = LayerSizer()  # wx.BoxSizer(wx.VERTICAL)
        
        for pn, pt in self.combinedPanelList:
            pt = _(pt)
            if isinstance(pn, basestring):
                if pn != "":
                    panel = ResourceOptionsPanel(self.ctrls.panelPages, pn)
                else:
                    if self.emptyPanel is None:
                        # Necessary to avoid a crash        
                        self.emptyPanel = DefaultOptionsPanel(self.ctrls.panelPages)
                    panel = self.emptyPanel
            else:
                # Factory function or class
                panel = pn(self.ctrls.panelPages, self, wx.GetApp())

            self.panelList.append(panel)
            self.ctrls.lbPages.Append(pt)
            mainsizer.Add(panel)
        
        
        self.ctrls.panelPages.SetSizer(mainsizer)
        self.ctrls.panelPages.SetMinSize(mainsizer.GetMinSize())

        self.ctrls.panelPages.Fit()
        self.Fit()

        self.ctrls.btnOk.SetId(wx.ID_OK)
        self.ctrls.btnCancel.SetId(wx.ID_CANCEL)

        # Transfer options to dialog
        for oct in self.combinedOptionToControl:
            o, c, t = oct[:3]
            self.idToOptionEntryMap[self.ctrls[c].GetId()] = oct
            self.oldSettings[o] = self.pWiki.getConfig().get("main", o)

            if t == "b":   # boolean field = checkbox
                self.ctrls[c].SetValue(
                        self.pWiki.getConfig().getboolean("main", o))
            elif t == "b3":   # boolean field = checkbox
                value = self.pWiki.getConfig().get("main", o)
                if value == "Gray":
                    self.ctrls[c].Set3StateValue(wx.CHK_UNDETERMINED)
                else:
                    if strToBool(value):
                        self.ctrls[c].Set3StateValue(wx.CHK_CHECKED)
                    else:
                        self.ctrls[c].Set3StateValue(wx.CHK_UNCHECKED)

#                 self.ctrls[c].SetValue(
#                         self.pWiki.getConfig().getboolean("main", o))
            elif t in ("t", "tre", "ttdf", "i0+", "f0+", "color0"):  # text field or regular expression field
                self.ctrls[c].SetValue(
                        uniToGui(self.pWiki.getConfig().get("main", o)) )
            elif t == "seli":   # Selection -> transfer index
                self.ctrls[c].SetSelection(
                        self.pWiki.getConfig().getint("main", o))
            elif t == "selt":   # Selection -> transfer content string
                try:
                    idx = oct[3].index(self.pWiki.getConfig().get("main", o))
                    self.ctrls[c].SetSelection(idx)
                except (IndexError, ValueError):
                    self.ctrls[c].SetStringSelection(
                        uniToGui(self.pWiki.getConfig().get("main", o)) )
            elif t == "spin":   # Numeric SpinCtrl -> transfer number
                self.ctrls[c].SetValue(
                        self.pWiki.getConfig().getint("main", o))
            elif t == "guilang":   # GUI language choice
                # First fill choice with options
                self.ctrls[c].Append(_(u"Default"))
                for ls, lt in Localization.getLangList():
                    self.ctrls[c].Append(lt)
                
                # Then select previous setting                
                optValue = self.pWiki.getConfig().get("main", o)
                self.ctrls[c].SetSelection(
                        Localization.findLangListIndex(optValue) + 1)


            # Register events for "..." buttons
            if t in ("color0", "ttdf"):
                params = oct[3:]
                if len(params) > 0:
                    # params[0] is name of the "..." button after the text field
                    dottedButtonId = self.ctrls[params[0]].GetId()
                    self.idToOptionEntryMap[dottedButtonId] = oct

                    wx.EVT_BUTTON(self, dottedButtonId,
                            self.OnDottedButtonPressed)

        # Options with special treatment
        self.ctrls.cbLowResources.SetValue(
                self.pWiki.getConfig().getint("main", "lowresources") != 0)

        self.ctrls.cbNewWindowWikiUrl.SetValue(
                self.pWiki.getConfig().getint("main",
                "new_window_on_follow_wiki_url") != 0)

        self.ctrls.chHtmlPreviewRenderer.Enable(
                WikiHtmlView.WikiHtmlViewIE is not None)
        
        wikiDocument = self.pWiki.getWikiDocument()
        if wikiDocument is not None:        
            self.ctrls.cbWikiReadOnly.SetValue(
                    wikiDocument.getWriteAccessDeniedByConfig())
        
        self.OnEditorImagePasteFileTypeChoice(None)

        self.activePageIndex = -1
        for panel in self.panelList:
            panel.Show(False)
            panel.Enable(False)

        self.ctrls.lbPages.SetSelection(0)
        self._refreshForPage()
        
        # Fixes focus bug under Linux
        self.SetFocus()

        wx.EVT_LISTBOX(self, GUI_ID.lbPages, self.OnLbPages)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)


        wx.EVT_BUTTON(self, GUI_ID.btnSelectFaceHtmlPrev, self.OnSelectFaceHtmlPrev)

        wx.EVT_BUTTON(self, GUI_ID.btnSelectClipCatchSoundFile,
                lambda evt: self.selectFile(self.ctrls.tfClipCatchSoundFile,
                _(u"Wave files (*.wav)|*.wav")))

        wx.EVT_BUTTON(self, GUI_ID.btnSelectExportDefaultDir,
                lambda evt: self.selectDirectory(self.ctrls.tfExportDefaultDir))

        wx.EVT_BUTTON(self, GUI_ID.btnSelectWikiOpenNewDefaultDir,
                lambda evt: self.selectDirectory(
                self.ctrls.tfWikiOpenNewDefaultDir))

        wx.EVT_BUTTON(self, GUI_ID.btnSelectFileLauncherPath,
                lambda evt: self.selectFile(self.ctrls.tfFileLauncherPath,
                _(u"All files (*.*)|*")))


        wx.EVT_CHOICE(self, GUI_ID.chEditorImagePasteFileType,
                self.OnEditorImagePasteFileTypeChoice)



    def _refreshForPage(self):
        if self.activePageIndex > -1:
            panel = self.panelList[self.activePageIndex]
            if not panel.setVisible(False):
                self.ctrls.lbPages.SetSelection(self.activePageIndex)
                return
            
            panel.Show(False)
            panel.Enable(False)

        self.activePageIndex = self.ctrls.lbPages.GetSelection()

        panel = self.panelList[self.activePageIndex]
        panel.setVisible(True)  # Not checking return value here

        # Enable appropriate addit. options panel
        panel.Enable(True)
        panel.Show(True)


    def getMainControl(self):
        return self.pWiki

    def OnLbPages(self, evt):
        self._refreshForPage()
        evt.Skip()


    def OnOk(self, evt):
        fieldsValid = True

        # First check validity of field contents
        for oct in self.combinedOptionToControl:
            o, c, t = oct[:3]

            if t == "tre":
                # Regular expression field, test if re is valid
                try:
                    rexp = guiToUni(self.ctrls[c].GetValue())
                    re.compile(rexp, re.DOTALL | re.UNICODE | re.MULTILINE)
                    self.ctrls[c].SetBackgroundColour(wx.WHITE)
                except:   # TODO Specific exception
                    fieldsValid = False
                    self.ctrls[c].SetBackgroundColour(wx.RED)
            elif t == "i0+":
                # Nonnegative integer field
                try:
                    val = int(guiToUni(self.ctrls[c].GetValue()))
                    if val < 0:
                        raise ValueError
                    self.ctrls[c].SetBackgroundColour(wx.WHITE)
                except ValueError:
                    fieldsValid = False
                    self.ctrls[c].SetBackgroundColour(wx.RED)
            elif t == "f0+":
                # Nonnegative float field
                try:
                    val = float(guiToUni(self.ctrls[c].GetValue()))
                    if val < 0:
                        raise ValueError
                    self.ctrls[c].SetBackgroundColour(wx.WHITE)
                except ValueError:
                    fieldsValid = False
                    self.ctrls[c].SetBackgroundColour(wx.RED)
            elif t == "color0":
                # HTML Color field or empty field
                val = guiToUni(self.ctrls[c].GetValue())
                rgb = htmlColorToRgbTuple(val)
                
                if val != "" and rgb is None:
                    self.ctrls[c].SetBackgroundColour(wx.RED)
                    fieldsValid = False
                else:
                    self.ctrls[c].SetBackgroundColour(wx.WHITE)
            elif t == "spin":
                # SpinCtrl
                try:
                    val = self.ctrls[c].GetValue()
                    if val < self.ctrls[c].GetMin() or \
                            val > self.ctrls[c].GetMax():
                        raise ValueError
                    self.ctrls[c].SetBackgroundColour(wx.WHITE)
                except ValueError:
                    fieldsValid = False
                    self.ctrls[c].SetBackgroundColour(wx.RED)


        if not fieldsValid:
            self.Refresh()
            return
            
        # Check each panel
        for i, panel in enumerate(self.panelList):
            if not panel.checkOk():
                # One panel has a problem (probably invalid data)
                self.ctrls.lbPages.SetSelection(i)
                self._refreshForPage()
                return

        
        # Options with special treatment (before standard handling)
        wikiDocument = self.pWiki.getWikiDocument()

        if wikiDocument is not None and not self.ctrls.cbWikiReadOnly.GetValue():
            wikiDocument.setWriteAccessDeniedByConfig(False)

        # Then transfer options from dialog to config object
        for oct in self.combinedOptionToControl:
            o, c, t = oct[:3]

            # TODO Handle unicode text controls
            if t == "b":
                self.pWiki.getConfig().set("main", o, repr(self.ctrls[c].GetValue()))
            elif t == "b3":
                value = self.ctrls[c].Get3StateValue()
                if value == wx.CHK_UNDETERMINED:
                    self.pWiki.getConfig().set("main", o, "Gray")
                elif value == wx.CHK_CHECKED:
                    self.pWiki.getConfig().set("main", o, "True")
                elif value == wx.CHK_UNCHECKED:
                    self.pWiki.getConfig().set("main", o, "False")

            elif t in ("t", "tre", "ttdf", "i0+", "f0+", "color0"):
                self.pWiki.getConfig().set(
                        "main", o, guiToUni(self.ctrls[c].GetValue()) )
            elif t == "seli":   # Selection -> transfer index
                self.pWiki.getConfig().set(
                        "main", o, unicode(self.ctrls[c].GetSelection()) )
            elif t == "selt":   # Selection -> transfer content string
                try:
                    self.pWiki.getConfig().set("main", o,
                            oct[3][self.ctrls[c].GetSelection()])
                except IndexError:
                    self.pWiki.getConfig().set("main", o, 
                            guiToUni(self.ctrls[c].GetStringSelection()))
            elif t == "spin":   # Numeric SpinCtrl -> transfer number
                self.pWiki.getConfig().set(
                        "main", o, unicode(self.ctrls[c].GetValue()) )
            elif t == "guilang":    # GUI language choice
                idx = self.ctrls[c].GetSelection()
                if idx < 1:
                    self.pWiki.getConfig().set("main", o, u"")
                else:
                    self.pWiki.getConfig().set("main", o,
                            Localization.getLangList()[idx - 1][0])

        # Options with special treatment (after standard handling)
        if self.ctrls.cbLowResources.GetValue():
            self.pWiki.getConfig().set("main", "lowresources", "1")
        else:
            self.pWiki.getConfig().set("main", "lowresources", "0")

        if self.ctrls.cbNewWindowWikiUrl.GetValue():
            self.pWiki.getConfig().set("main", "new_window_on_follow_wiki_url", "1")
        else:
            self.pWiki.getConfig().set("main", "new_window_on_follow_wiki_url", "0")

        if wikiDocument is not None and self.ctrls.cbWikiReadOnly.GetValue():
            wikiDocument.setWriteAccessDeniedByConfig(True)

        # Ok for each panel
        for panel in self.panelList:
            panel.handleOk()

        self.pWiki.getConfig().informChanged(self.oldSettings)

        evt.Skip()


    def getOldSettings(self):
        return self.oldSettings


    def OnSelectFaceHtmlPrev(self, evt):
        dlg = FontFaceDialog(self, -1, self.pWiki,
                self.ctrls.tfFacenameHtmlPreview.GetValue())
        if dlg.ShowModal() == wx.ID_OK:
            self.ctrls.tfFacenameHtmlPreview.SetValue(dlg.GetValue())
        dlg.Destroy()
        
#     def OnSelectPageStatusTimeFormat(self, evt):
#         dlg = DateformatDialog(self, -1, self.pWiki, 
#                 deffmt=self.ctrls.tfPageStatusTimeFormat.GetValue())
#         if dlg.ShowModal() == wx.ID_OK:
#             self.ctrls.tfPageStatusTimeFormat.SetValue(dlg.GetValue())
#         dlg.Destroy()

    def OnEditorImagePasteFileTypeChoice(self, evt):
        enabled = self.ctrls.chEditorImagePasteFileType.GetSelection() == 2
        self.ctrls.tfEditorImagePasteQuality.Enable(enabled)


    def OnDottedButtonPressed(self, evt):
        """
        Called when a "..." button is pressed (for some of them) to show
        an alternative way to specify the input, e.g. showing a color selector
        for color entries instead of using the bare text field
        """
        oct = self.idToOptionEntryMap[evt.GetId()]
        o, c, t = oct[:3]
        params = oct[3:]
        
        if t == "color0":
            self.selectColor(self.ctrls[c])
        elif t == "ttdf":   # Date/time format
            self.selectDateTimeFormat(self.ctrls[c])


    def selectColor(self, tfield):
        rgb = htmlColorToRgbTuple(tfield.GetValue())
        if rgb is None:
            rgb = 0, 0, 0

        color = wx.Colour(*rgb)
        colordata = wx.ColourData()
        colordata.SetColour(color)

        dlg = wx.ColourDialog(self, colordata)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                color = dlg.GetColourData().GetColour()
                if color.Ok():
                    tfield.SetValue(
                            rgbToHtmlColor(color.Red(), color.Green(),
                            color.Blue()))
        finally:
            dlg.Destroy()


    def selectDirectory(self, tfield):        
        seldir = wx.DirSelector(_(u"Select Directory"),
                tfield.GetValue(),
                style=wx.DD_DEFAULT_STYLE|wx.DD_NEW_DIR_BUTTON, parent=self)
            
        if seldir:
            tfield.SetValue(seldir)

    def selectFile(self, tfield, wildcard=u""):        
        selfile = wx.FileSelector(_(u"Select File"),
                tfield.GetValue(), wildcard = wildcard + u"|" + \
                        _(u"All files (*.*)|*"),
                flags=wx.OPEN, parent=self)
            
        if selfile:
            tfield.SetValue(selfile)
            
    def selectDateTimeFormat(self, tfield):
        dlg = DateformatDialog(self, -1, self.pWiki, 
                deffmt=tfield.GetValue())
        try:
            if dlg.ShowModal() == wx.ID_OK:
                tfield.SetValue(dlg.GetValue())
        finally:
            dlg.Destroy()


