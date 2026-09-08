PROGRAM POUexecute
VAR
	iCount:INT;
	
	t1: TON;
	output: BOOL;
	e1: TIME;
	in1: BOOL;
	a: BOOL;
	b: BOOL;
	c: BOOL;
	out1: BOOL;
	t2: TON;
	out2: INT;
END_VAR

NETWORK 0 LD
  LET en1 := TRUE;
  IF en1 THEN
  EXECUTE
iCount:=icount+1;
  END_EXECUTE
  END_IF
END_NETWORK
NETWORK 1 LD
  output := t1(IN := in1, PT := e1);
END_NETWORK
NETWORK 2 LD
  LET g1 := b;
  out1 := ((a OR g1) AND c);
  out2 := g1;
END_NETWORK
NETWORK 3 LD
  output := t2(IN := , PT := e1);
END_NETWORK

END_PROGRAM
