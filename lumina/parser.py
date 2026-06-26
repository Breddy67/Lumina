# lumina/parser.py
"""Parser for the Lumina language."""

from typing import List, Tuple, Optional, Union, Callable

import lumina_ast as ast
import tokeniser as tok
from errors import raise_parse_error


def parse_error_eof(msg: str) -> None:
    """Raise a parse error for end of input."""
    raise_parse_error(f"{msg} (end of input)")


def parse_error_at_token(t: tok.Token, msg: str) -> None:
    """Raise a parse error at a specific token."""
    raise_parse_error(f"Parse error at {t.pos}, token {tok.token_to_str(t.kind)}('{t.text}'): {msg}")


def parse_fail(tokens: List[tok.Token], msg: str) -> None:
    """Raise a parse error."""
    if tokens:
        parse_error_at_token(tokens[0], msg)
    else:
        parse_error_eof(msg)


def check(tokens: List[tok.Token], expected: tok.TokenKind) -> Tuple[tok.Token, List[tok.Token]]:
    """Check that the next token is of the expected kind."""
    if not tokens:
        parse_error_eof(f"Expected {tok.token_to_str(expected)}")
    if tokens[0].kind != expected:
        parse_error_at_token(tokens[0], f"Expected token {tok.token_to_str(expected)} but got {tok.token_to_str(tokens[0].kind)}")
    return tokens[0], tokens[1:]


def is_primitive_type(text: str) -> bool:
    """Check if a string is a primitive type name."""
    return text in ["Num", "Str", "Bool", "Color", "Vec2", "Vec3"]


# Type expression parsing
def parse_type_expr(tokens: List[tok.Token]) -> Tuple[ast.TypeExpr, List[tok.Token]]:
    """Parse a type expression."""
    if not tokens:
        parse_error_eof("Unexpected end of input while parsing type expression")

    t = tokens[0]
    if t.kind == tok.TokenKind.IDENT and is_primitive_type(t.text):
        base = ast.TPrim(t.text)
        return parse_type_expr_suffix(base, tokens[1:])
    elif t.kind == tok.TokenKind.LBRACKET:
        inner_type, tokens = parse_type_expr(tokens[1:])
        _, tokens = check(tokens, tok.TokenKind.RBRACKET)
        return parse_type_expr_suffix(ast.TArray(inner_type), tokens)
    elif t.kind == tok.TokenKind.LPAREN:
        types, tokens = parse_tuple_types(tokens[1:])
        return parse_type_expr_suffix(ast.TTuple(types), tokens)
    else:
        parse_error_at_token(t, "Expected type expression (primitive type, array type, or tuple type)")


def parse_type_expr_suffix(base_type: ast.TypeExpr, tokens: List[tok.Token]) -> Tuple[ast.TypeExpr, List[tok.Token]]:
    """Parse suffixes for type expressions."""
    if tokens and tokens[0].kind == tok.TokenKind.LBRACKET:
        _, tokens = check(tokens[1:], tok.TokenKind.RBRACKET)
        return parse_type_expr_suffix(ast.TArray(base_type), tokens)
    return base_type, tokens


def parse_tuple_types(tokens: List[tok.Token]) -> Tuple[List[ast.TypeExpr], List[tok.Token]]:
    """Parse tuple types."""
    first, tokens = parse_type_expr(tokens)

    def parse_items(acc: List[ast.TypeExpr], tokens: List[tok.Token]) -> Tuple[List[ast.TypeExpr], List[tok.Token]]:
        if not tokens:
            parse_error_eof("Unexpected end while parsing tuple type")
        if tokens[0].kind == tok.TokenKind.COMMA:
            item, tokens = parse_type_expr(tokens[1:])
            return parse_items([item] + acc, tokens)
        elif tokens[0].kind == tok.TokenKind.RPAREN:
            return list(reversed([first] + acc)), tokens[1:]
        else:
            parse_fail(tokens, "Expected ',' or ')' in tuple type")

    return parse_items([], tokens)


# Expression parsing
def parse_expr(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse an expression."""
    return parse_logical_expr(tokens)


def parse_logical_expr(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse a logical expression."""
    left, tokens = parse_compare_expr(tokens)

    def parse_logical(expr: ast.Expr, tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
        if not tokens:
            return expr, tokens
        if tokens[0].kind == tok.TokenKind.AND:
            right, tokens = parse_compare_expr(tokens[1:])
            return parse_logical(ast.Binop(ast.BinOp.AND, expr, right), tokens)
        if tokens[0].kind == tok.TokenKind.OR:
            right, tokens = parse_compare_expr(tokens[1:])
            return parse_logical(ast.Binop(ast.BinOp.OR, expr, right), tokens)
        return expr, tokens

    return parse_logical(left, tokens)


def parse_compare_expr(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse a comparison expression."""
    left, tokens = parse_math_expr(tokens)

    def parse_compare(expr: ast.Expr, tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
        if not tokens:
            return expr, tokens
        if tokens[0].kind in [tok.TokenKind.EQ_EQ, tok.TokenKind.NOT_EQ,
                               tok.TokenKind.LESS, tok.TokenKind.GREATER,
                               tok.TokenKind.LESS_EQ, tok.TokenKind.GREATER_EQ]:
            op = tokens[0].kind
            right, tokens = parse_math_expr(tokens[1:])
            op_map = {
                tok.TokenKind.EQ_EQ: ast.BinOp.EQ,
                tok.TokenKind.NOT_EQ: ast.BinOp.NOT_EQ,
                tok.TokenKind.LESS: ast.BinOp.LT,
                tok.TokenKind.GREATER: ast.BinOp.GT,
                tok.TokenKind.LESS_EQ: ast.BinOp.LTEQ,
                tok.TokenKind.GREATER_EQ: ast.BinOp.GTEQ,
            }
            return parse_compare(ast.Binop(op_map[op], expr, right), tokens)
        return expr, tokens

    return parse_compare(left, tokens)


def parse_math_expr(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse a mathematical expression."""
    left, tokens = parse_term(tokens)

    def parse_math(expr: ast.Expr, tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
        if not tokens:
            return expr, tokens
        if tokens[0].kind == tok.TokenKind.PLUS:
            right, tokens = parse_term(tokens[1:])
            return parse_math(ast.Binop(ast.BinOp.ADD, expr, right), tokens)
        if tokens[0].kind == tok.TokenKind.MINUS:
            right, tokens = parse_term(tokens[1:])
            return parse_math(ast.Binop(ast.BinOp.SUB, expr, right), tokens)
        return expr, tokens

    return parse_math(left, tokens)


def parse_term(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse a term."""
    left, tokens = parse_factor(tokens)

    def parse_terms(expr: ast.Expr, tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
        if not tokens:
            return expr, tokens
        if tokens[0].kind == tok.TokenKind.STAR:
            right, tokens = parse_factor(tokens[1:])
            return parse_terms(ast.Binop(ast.BinOp.MUL, expr, right), tokens)
        if tokens[0].kind == tok.TokenKind.SLASH:
            right, tokens = parse_factor(tokens[1:])
            return parse_terms(ast.Binop(ast.BinOp.DIV, expr, right), tokens)
        return expr, tokens

    return parse_terms(left, tokens)


def parse_factor(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse a factor."""
    if not tokens:
        parse_error_eof("Unexpected end of program")

    if tokens[0].kind == tok.TokenKind.MINUS:
        right, tokens = parse_primary(tokens[1:])
        return ast.Unop(ast.UnOp.NEG, right), tokens
    if tokens[0].kind == tok.TokenKind.NOT:
        right, tokens = parse_primary(tokens[1:])
        return ast.Unop(ast.UnOp.NOT, right), tokens

    return parse_primary(tokens)


def parse_primary(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse a primary expression."""
    if not tokens:
        parse_error_eof("Unexpected end of program")

    t = tokens[0]

    # Time literal
    if t.kind == tok.TokenKind.TIME:
        v = t.value
        if v.endswith('ms'):
            return ast.Time(float(v[:-2]), "ms"), tokens[1:]
        elif v.endswith('s'):
            return ast.Time(float(v[:-1]), "s"), tokens[1:]
        else:
            parse_error_at_token(t, "invalid time literal")

    # Number literal
    if t.kind == tok.TokenKind.NUMBER:
        return ast.Num(float(t.value)), tokens[1:]

    # String literal
    if t.kind == tok.TokenKind.STRING:
        return ast.Str(t.value), tokens[1:]

    # Boolean literal
    if t.kind == tok.TokenKind.BOOL:
        return ast.Bool(t.value == "true"), tokens[1:]

    # Color literal
    if t.kind == tok.TokenKind.COLOR:
        return ast.ColorLiteral(t.value), tokens[1:]

    # Identifier or call or access
    if t.kind == tok.TokenKind.IDENT:
        if len(tokens) >= 2 and tokens[1].kind == tok.TokenKind.LPAREN:
            return parse_call(tokens)
        elif len(tokens) >= 2 and (tokens[1].kind == tok.TokenKind.LBRACKET or tokens[1].kind == tok.TokenKind.DOT):
            return parse_access(tokens)
        else:
            return ast.Ident(t.text), tokens[1:]

    # Parenthesized expression or tuple
    if t.kind == tok.TokenKind.LPAREN:
        try:
            tup, tokens = parse_tuple(tokens)
            return tup, tokens
        except:
            expr, tokens = parse_expr(tokens[1:])
            _, tokens = check(tokens, tok.TokenKind.RPAREN)
            return expr, tokens

    # Array literal
    if t.kind == tok.TokenKind.LBRACKET:
        arr, tokens = parse_array(tokens)
        return arr, tokens

    parse_error_at_token(t, "Unexpected token in expression")


def parse_tuple(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse a tuple expression."""
    _, tokens = check(tokens, tok.TokenKind.LPAREN)
    first, tokens = parse_expr(tokens)
    _, tokens = check(tokens, tok.TokenKind.COMMA)
    second, tokens = parse_expr(tokens)

    def get_items(tokens: List[tok.Token], items: List[ast.Expr]) -> Tuple[List[ast.Expr], List[tok.Token]]:
        if not tokens:
            return items, tokens
        if tokens[0].kind == tok.TokenKind.COMMA:
            item, tokens = parse_expr(tokens[1:])
            return get_items(tokens, items + [item])
        elif tokens[0].kind == tok.TokenKind.RPAREN:
            return items, tokens[1:]
        else:
            parse_fail(tokens, "Unexpected token in tuple")

    items, tokens = get_items(tokens, [])
    return ast.Tuple(first, second, items), tokens


def parse_array(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse an array expression."""
    _, tokens = check(tokens, tok.TokenKind.LBRACKET)

    def get_items(tokens: List[tok.Token], items: List[ast.Expr]) -> Tuple[List[ast.Expr], List[tok.Token]]:
        if not tokens:
            return items, tokens
        if tokens[0].kind == tok.TokenKind.RBRACKET:
            return items, tokens[1:]
        item, tokens = parse_expr(tokens)
        if tokens and tokens[0].kind == tok.TokenKind.COMMA:
            tokens = tokens[1:]
        return get_items(tokens, items + [item])

    items, tokens = get_items(tokens, [])
    return ast.Array(items), tokens


def parse_call(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse a function call."""
    if not tokens or tokens[0].kind != tok.TokenKind.IDENT:
        parse_fail(tokens, "Expected function name")

    name = tokens[0].text
    _, tokens = check(tokens[1:], tok.TokenKind.LPAREN)

    def parse_arg(tokens: List[tok.Token]) -> Tuple[ast.CallArg, List[tok.Token]]:
        if len(tokens) >= 2 and tokens[0].kind == tok.TokenKind.IDENT and tokens[1].kind == tok.TokenKind.EQ:
            arg_name = tokens[0].text
            expr, tokens = parse_expr(tokens[2:])
            return ast.NameArg(arg_name, expr), tokens
        else:
            expr, tokens = parse_expr(tokens)
            return ast.PosArg(expr), tokens

    def parse_args(acc: List[ast.CallArg], tokens: List[tok.Token]) -> Tuple[List[ast.CallArg], List[tok.Token]]:
        if not tokens:
            parse_error_eof("Unclosed function call")
        if tokens[0].kind == tok.TokenKind.RPAREN:
            return list(reversed(acc)), tokens[1:]
        arg, tokens = parse_arg(tokens)
        if tokens and tokens[0].kind == tok.TokenKind.COMMA:
            return parse_args([arg] + acc, tokens[1:])
        elif tokens and tokens[0].kind == tok.TokenKind.RPAREN:
            return list(reversed([arg] + acc)), tokens[1:]
        else:
            parse_fail(tokens, "Expected ',' or ')' in argument list")

    if tokens and tokens[0].kind == tok.TokenKind.RPAREN:
        return ast.Call(name, []), tokens[1:]

    args, tokens = parse_args([], tokens)
    return ast.Call(name, args), tokens


def parse_access(tokens: List[tok.Token]) -> Tuple[ast.Expr, List[tok.Token]]:
    """Parse an access expression."""
    if not tokens or tokens[0].kind != tok.TokenKind.IDENT:
        parse_fail(tokens, "Expected identifier for accessor")

    name = tokens[0].text
    base = ast.Ident(name)
    tokens = tokens[1:]

    def parse_suffixes(acc: List[ast.AccessSuffix], tokens: List[tok.Token]) -> Tuple[List[ast.AccessSuffix], List[tok.Token]]:
        if not tokens:
            return list(reversed(acc)), tokens
        if tokens[0].kind == tok.TokenKind.DOT:
            if len(tokens) < 2 or tokens[1].kind != tok.TokenKind.IDENT:
                parse_fail(tokens, "Expected field name after '.'")
            return parse_suffixes([ast.Field(tokens[1].text)] + acc, tokens[2:])
        if tokens[0].kind == tok.TokenKind.LBRACKET:
            index_expr, tokens = parse_expr(tokens[1:])
            if not tokens or tokens[0].kind != tok.TokenKind.RBRACKET:
                parse_fail(tokens, "Expected ']'")
            return parse_suffixes([ast.Index(index_expr)] + acc, tokens[1:])
        return list(reversed(acc)), tokens

    suffixes, tokens = parse_suffixes([], tokens)
    if not suffixes:
        return base, tokens
    return ast.Access(base, suffixes), tokens


def parse_ident_access(tokens: List[tok.Token]) -> Tuple[ast.Accessor, List[tok.Token]]:
    """Parse an identifier access for assignment."""
    if not tokens or tokens[0].kind != tok.TokenKind.IDENT:
        parse_fail(tokens, "Expected identifier for accessor")

    name = tokens[0].text
    tokens = tokens[1:]

    def parse_suffixes(acc: List[ast.AccessSuffix], tokens: List[tok.Token]) -> Tuple[List[ast.AccessSuffix], List[tok.Token]]:
        if not tokens:
            return list(reversed(acc)), tokens
        if tokens[0].kind == tok.TokenKind.DOT:
            if len(tokens) < 2 or tokens[1].kind != tok.TokenKind.IDENT:
                parse_fail(tokens, "Expected field name after '.'")
            return parse_suffixes([ast.Field(tokens[1].text)] + acc, tokens[2:])
        if tokens[0].kind == tok.TokenKind.LBRACKET:
            index_expr, tokens = parse_expr(tokens[1:])
            if not tokens or tokens[0].kind != tok.TokenKind.RBRACKET:
                parse_fail(tokens, "Expected ']'")
            return parse_suffixes([ast.Index(index_expr)] + acc, tokens[1:])
        return list(reversed(acc)), tokens

    suffixes, tokens = parse_suffixes([], tokens)
    return ast.Accessor(name, suffixes), tokens


# Statement parsing
def parse_statement(tokens: List[tok.Token]) -> Tuple[ast.Stmt, List[tok.Token]]:
    """Parse a statement."""
    if not tokens:
        parse_error_eof("Unexpected end of program")

    if tokens[0].kind == tok.TokenKind.LET:
        return parse_let(tokens)
    if tokens[0].kind == tok.TokenKind.DRAW:
        return parse_draw(tokens)
    if tokens[0].kind == tok.TokenKind.RETURN:
        return parse_return(tokens)
    if tokens[0].kind == tok.TokenKind.IF:
        return parse_if(tokens)
    if tokens[0].kind == tok.TokenKind.FOR:
        return parse_for(tokens)

    # Check if it's an assignment - look for identifier followed by =, +=, or -=
    if len(tokens) >= 2 and tokens[0].kind == tok.TokenKind.IDENT:
        # Check if the next token is an assignment operator
        if tokens[1].kind in [tok.TokenKind.EQ, tok.TokenKind.PLUS_EQ, tok.TokenKind.MINUS_EQ]:
            # It's an assignment - parse it as one
            return parse_assignment(tokens)

    # Otherwise, parse as an expression statement
    expr, tokens = parse_expr(tokens)
    return ast.ExprStmt(expr), tokens

def parse_assignment(tokens: List[tok.Token]) -> Tuple[ast.Stmt, List[tok.Token]]:
    """Parse an assignment statement."""
    lhs, tokens = parse_ident_access(tokens)
    if not tokens:
        parse_fail(tokens, "Expected assignment operator")

    if tokens[0].kind == tok.TokenKind.EQ:
        rhs, tokens = parse_expr(tokens[1:])
        return ast.Assign(lhs, ast.AssignOp.SET, rhs), tokens
    elif tokens[0].kind == tok.TokenKind.PLUS_EQ:
        rhs, tokens = parse_expr(tokens[1:])
        return ast.Assign(lhs, ast.AssignOp.PLUS_SET, rhs), tokens
    elif tokens[0].kind == tok.TokenKind.MINUS_EQ:
        rhs, tokens = parse_expr(tokens[1:])
        return ast.Assign(lhs, ast.AssignOp.MINUS_SET, rhs), tokens
    else:
        parse_fail(tokens, "Expected assignment operator")


def parse_let(tokens: List[tok.Token]) -> Tuple[ast.Stmt, List[tok.Token]]:
    """Parse a let binding."""
    _, tokens = check(tokens, tok.TokenKind.LET)
    name_token, tokens = check(tokens, tok.TokenKind.IDENT)

    # Optional type annotation
    if tokens and tokens[0].kind == tok.TokenKind.COLON:
        typ, tokens = parse_type_expr(tokens[1:])
        type_annotation = typ
    else:
        type_annotation = None

    _, tokens = check(tokens, tok.TokenKind.EQ)
    expr, tokens = parse_expr(tokens)

    return ast.Let(name_token.text, type_annotation, expr), tokens


def parse_return(tokens: List[tok.Token]) -> Tuple[ast.Stmt, List[tok.Token]]:
    """Parse a return statement."""
    _, tokens = check(tokens, tok.TokenKind.RETURN)
    expr, tokens = parse_expr(tokens)
    return ast.Return(expr), tokens


def parse_draw(tokens: List[tok.Token]) -> Tuple[ast.Stmt, List[tok.Token]]:
    """Parse a draw statement."""
    _, tokens = check(tokens, tok.TokenKind.DRAW)
    expr, tokens = parse_expr(tokens)
    return ast.Draw(expr), tokens


def parse_block(tokens: List[tok.Token]) -> Tuple[List[ast.Stmt], List[tok.Token]]:
    """Parse a block."""
    _, tokens = check(tokens, tok.TokenKind.LBRACE)

    def get_items(tokens: List[tok.Token], acc: List[ast.Stmt]) -> Tuple[List[ast.Stmt], List[tok.Token]]:
        if not tokens:
            parse_fail(tokens, "Unclosed block: expected '}'")
        if tokens[0].kind == tok.TokenKind.RBRACE:
            return list(reversed(acc)), tokens[1:]
        stmt, tokens = parse_statement(tokens)
        return get_items(tokens, [stmt] + acc)

    return get_items(tokens, [])


# Top-level parsing
def parse_fn(tokens: List[tok.Token]) -> Tuple[ast.TopLevel, List[tok.Token]]:
    """Parse a function declaration."""
    _, tokens = check(tokens, tok.TokenKind.FN)
    name_token, tokens = check(tokens, tok.TokenKind.IDENT)
    _, tokens = check(tokens, tok.TokenKind.LPAREN)

    def get_params(tokens: List[tok.Token], acc: List[Tuple[str, Optional[ast.TypeExpr]]]) -> Tuple[List[Tuple[str, Optional[ast.TypeExpr]]], List[tok.Token]]:
        if not tokens:
            parse_fail(tokens, "Expected parameter or ')'")
        if tokens[0].kind == tok.TokenKind.RPAREN:
            return list(reversed(acc)), tokens[1:]
        if tokens[0].kind != tok.TokenKind.IDENT:
            parse_fail(tokens, "Expected parameter name")

        param = tokens[0].text
        tokens = tokens[1:]

        # Optional type annotation
        if tokens and tokens[0].kind == tok.TokenKind.COLON:
            typ, tokens = parse_type_expr(tokens[1:])
            type_annotation = typ
        else:
            type_annotation = None

        if tokens and tokens[0].kind == tok.TokenKind.COMMA:
            return get_params(tokens[1:], [(param, type_annotation)] + acc)
        elif tokens and tokens[0].kind == tok.TokenKind.RPAREN:
            return list(reversed([(param, type_annotation)] + acc)), tokens[1:]
        else:
            parse_fail(tokens, "Expected ',' or ')' after parameter")

    if tokens and tokens[0].kind == tok.TokenKind.RPAREN:
        params = []
        tokens = tokens[1:]
    else:
        params, tokens = get_params(tokens, [])

    block, tokens = parse_block(tokens)
    return ast.FnDecl(name_token.text, params, block), tokens


def parse_loop(tokens: List[tok.Token]) -> Tuple[ast.TopLevel, List[tok.Token]]:
    """Parse a loop block."""
    _, tokens = check(tokens, tok.TokenKind.LOOP)
    block, tokens = parse_block(tokens)
    return ast.LoopBlock(block), tokens


def parse_event_block(tokens: List[tok.Token]) -> Tuple[ast.TopLevel, List[tok.Token]]:
    """Parse an event block."""
    _, tokens = check(tokens, tok.TokenKind.ON)
    expr, tokens = parse_expr(tokens)
    block, tokens = parse_block(tokens)
    return ast.EventBlock(expr, block), tokens


def parse_time_block(tokens: List[tok.Token]) -> Tuple[ast.TopLevel, List[tok.Token]]:
    """Parse a time block."""
    _, tokens = check(tokens, tok.TokenKind.EVERY)
    expr, tokens = parse_expr(tokens)
    block, tokens = parse_block(tokens)
    return ast.TimeBlock(expr, block), tokens


def parse_if(tokens: List[tok.Token]) -> Tuple[ast.Stmt, List[tok.Token]]:
    """Parse an if statement."""
    _, tokens = check(tokens, tok.TokenKind.IF)
    _, tokens = check(tokens, tok.TokenKind.LPAREN)
    cond, tokens = parse_expr(tokens)
    _, tokens = check(tokens, tok.TokenKind.RPAREN)
    then_body, tokens = parse_block(tokens)

    # Check for else or elif
    if tokens and tokens[0].kind == tok.TokenKind.ELSE:
        if len(tokens) >= 2 and tokens[1].kind == tok.TokenKind.IF:
            # elif
            elif_stmt, tokens = parse_if(tokens[1:])
            return ast.If(cond, then_body, [elif_stmt]), tokens
        else:
            else_body, tokens = parse_block(tokens[1:])
            return ast.If(cond, then_body, else_body), tokens

    return ast.If(cond, then_body, None), tokens


def parse_for(tokens: List[tok.Token]) -> Tuple[ast.Stmt, List[tok.Token]]:
    """Parse a for loop."""
    _, tokens = check(tokens, tok.TokenKind.FOR)
    name_token, tokens = check(tokens, tok.TokenKind.IDENT)
    _, tokens = check(tokens, tok.TokenKind.IN)
    expr, tokens = parse_expr(tokens)
    block, tokens = parse_block(tokens)
    return ast.For(name_token.text, expr, block), tokens


def parse_top_level(tokens: List[tok.Token]) -> Tuple[ast.TopLevel, List[tok.Token]]:
    """Parse a top-level declaration."""
    if not tokens:
        parse_error_eof("Unexpected end of program")

    if tokens[0].kind == tok.TokenKind.FN:
        return parse_fn(tokens)
    if tokens[0].kind == tok.TokenKind.ON:
        return parse_event_block(tokens)
    if tokens[0].kind == tok.TokenKind.EVERY:
        return parse_time_block(tokens)
    if tokens[0].kind == tok.TokenKind.LOOP:
        return parse_loop(tokens)

    stmt, tokens = parse_statement(tokens)
    return stmt, tokens


# Program parsing
def parse_program(tokens: List[tok.Token]) -> Tuple[ast.Program, List[tok.Token]]:
    """Parse a complete program."""
    def get_imports(tokens: List[tok.Token], acc: List[ast.Import]) -> Tuple[List[ast.Import], List[tok.Token]]:
        if tokens and tokens[0].kind == tok.TokenKind.IMPORT:
            imp, tokens = parse_import(tokens)
            return get_imports(tokens, [imp] + acc)
        return list(reversed(acc)), tokens

    imports, tokens = get_imports(tokens, [])

    # Parse config block
    if tokens and tokens[0].kind == tok.TokenKind.CONFIG:
        config, tokens = parse_config_block(tokens)
    else:
        config = []

    def get_items(tokens: List[tok.Token], acc: List[ast.TopLevel]) -> Tuple[List[ast.TopLevel], List[tok.Token]]:
        if not tokens:
            return list(reversed(acc)), tokens
        item, tokens = parse_top_level(tokens)
        return get_items(tokens, [item] + acc)

    items, tokens = get_items(tokens, [])
    return ast.Program(imports, config, items), tokens


def parse_import(tokens: List[tok.Token]) -> Tuple[ast.Import, List[tok.Token]]:
    """Parse an import declaration."""
    _, tokens = check(tokens, tok.TokenKind.IMPORT)
    name_token, tokens = check(tokens, tok.TokenKind.IDENT)
    _, tokens = check(tokens, tok.TokenKind.FROM)
    from_token, tokens = check(tokens, tok.TokenKind.STRING)
    return ast.Import(name_token.text, from_token.value), tokens


def parse_config_block(tokens: List[tok.Token]) -> Tuple[List[Tuple[str, ast.Expr]], List[tok.Token]]:
    """Parse a config block."""
    _, tokens = check(tokens, tok.TokenKind.CONFIG)
    _, tokens = check(tokens, tok.TokenKind.LBRACE)

    def get_items(tokens: List[tok.Token], acc: List[Tuple[str, ast.Expr]]) -> Tuple[List[Tuple[str, ast.Expr]], List[tok.Token]]:
        if tokens and tokens[0].kind == tok.TokenKind.RBRACE:
            return list(reversed(acc)), tokens[1:]
        key_token, tokens = check(tokens, tok.TokenKind.IDENT)
        _, tokens = check(tokens, tok.TokenKind.EQ)
        value, tokens = parse_expr(tokens)
        return get_items(tokens, [(key_token.text, value)] + acc)

    return get_items(tokens, [])


def parse(tokens: List[tok.Token]) -> ast.Program:
    """Parse tokens into a program."""
    # Filter out NEWLINE tokens
    tokens = [t for t in tokens if t.kind != tok.TokenKind.NEWLINE]

    prog, remaining = parse_program(tokens)

    if remaining:
        raise_parse_error(f"Unexpected token at end of program: {tok.print_token(remaining[0])}")

    return prog