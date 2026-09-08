PROGRAM ErrorHandling
VAR
	dummy	: BOOL;
END_VAR

END_PROGRAM

METHOD PROTECTED Initialize
// Connect Lenze module handlers to this base module handler

GlobalVars.fbModuleManager.ModuleHandler.SetParent(
	ModuleHandlerParent	:= ModuleHandler);
END_METHOD
