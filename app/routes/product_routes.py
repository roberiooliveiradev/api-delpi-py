from fastapi import APIRouter, HTTPException, Query
from app.services.product_service import get_product, get_products, get_structure, get_parents, get_guide, get_inspection, get_product_analyser, get_customers, get_structure_excel
from app.services.product_service import get_suppliers, get_inbound_invoice_items, get_outbound_invoice_items, get_stock, search_products, search_products_by_description
from app.core.responses import success_response, error_response
from app.core.exceptions import DatabaseConnectionError
from app.utils.logger import log_info, log_error
from app.repositories.base_repository import BaseRepository
from pydantic import BaseModel
from typing import Optional
from app.models.product_model import ProductSearchRequest
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/", summary="Listagem de produtos com limite")
def products(limit: int = Query(50, ge=1, le=200)):
    """
    Retorna uma lista de produtos com limite opcional (padrão = 10).
    """
    try:
        products = get_products(limit)
        return success_response(
            data={"total": len(products), "produtos": [p.model_dump(by_alias=True) for p in products]},
            message="Listagem realizada com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao listar produtos: {e}")
        return error_response(f"Erro inesperado: {e}")
    
@router.get(
    "/search/description",
    summary="Busca específica por descrição, com paginação e score"
)
def search_products_by_description_route(
    description: str = Query(..., description="Descrição ou termos"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    try:
        result = search_products_by_description(description, page, page_size)
        return success_response(
            data=result,
            message=f"Busca por descrição realizada com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro na busca pela descrição: {e}")
        return error_response(f"Erro inesperado: {e}")


@router.post("/search", summary="Pesquisa de produtos via POST, com filtros e paginação")
def search_products_post_route(body: ProductSearchRequest):
    try:
        result = search_products(
            body.page,
            body.page_size,
            body.code,
            body.description,
            body.group
        )
        return success_response(
            data=result,
            message=f"Pesquisa de produtos realizada com sucesso (página {body.page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao pesquisar produtos: {e}")
        return error_response(f"Erro inesperado: {e}")
    

@router.get("/{code}", summary="Consulta produto por código")
def product(code: str):
    try:
        product = get_product(code)
        return success_response(
            data={"produto": product.model_dump(by_alias=True)},
            message="Produto localizado com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao consultar produto {code}: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get("/{code}/structure", summary="Consulta estrutura (BOM) paginada via CTE")
def structure(
    code: str,
    max_depth: int = Query(10, ge=1, le=15),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500)
):
    """
    Retorna a estrutura (BOM) via CTE com suporte a paginação.
    """
    try:
        result = get_structure(code, max_depth, page, page_size)
        return success_response(
            data=result,
            message=f"Estrutura do produto {code} retornada com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar estrutura do produto {code}: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get(
    "/{code}/structure/excel",
    summary="Exporta a estrutura formatada em planilha Excel (público)",
    include_in_schema=True
)
async def structure_excel_public(code: str, download: bool = False):
    """
    Retorna o link clicável para download ou o arquivo Excel, conforme o parâmetro 'download'.
    """
    try:
        # Gera o arquivo Excel na memória
        excel_file = get_structure_excel(code)
        filename = f"Estrutura_{code}.xlsx"

        # ✅ Se for chamado com download=true, retorna o arquivo diretamente
        if download:
            return StreamingResponse(
                excel_file,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Cache-Control": "public, max-age=86400"
                }
            )

        # ✅ Caso contrário, retorna o link clicável
        public_url = f"https://api.transformamaisdelpi.com.br/products/{code}/structure/excel?download=true"
        html_link = f'<a href="{public_url}" target="_blank" rel="noopener noreferrer">📂 Baixar Estrutura {code}</a>'

        return JSONResponse(
            content={
                "message": "Arquivo Excel gerado com sucesso!",
                "download_url": public_url,
                "html_link": html_link
            }
        )

    except Exception as e:
        log_error(f"Erro ao gerar planilha Excel pública de {code}: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/{code}/parents", summary="Consulta produtos pai (Where Used) paginada via CTE")
def parents(
    code: str,
    max_depth: int = Query(10, ge=1, le=15),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500)
):
    """
    Retorna produtos pai (Where Used) via CTE com paginação.
    """
    try:
        result = get_parents(code, max_depth, page, page_size)
        return success_response(
            data=result,
            message=f"Produtos pai de {code} retornados com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar pais do item {code}: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get("/{code}/suppliers", summary="Consulta os fornecedores de um produto com paginação")
def suppliers(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    """
    Retorna os fornecedores de um produto com suporte a paginação.
    """
    try:
        result = get_suppliers(code, page, page_size)
        return success_response(
            data=result,
            message=f"Fornecedores de {code} retornados com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar fornecedores do item {code}: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get("/{code}/inbound-invoice-items", summary="Consulta as notas fiscais de entrada (paginadas e filtráveis)")
def inbound_invoice_items(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    issue_date_start: Optional[str] = Query(None),
    issue_date_end: Optional[str] = Query(None),
    supplier: Optional[str] = Query(None),
    branch: Optional[str] = Query(None)
):
    """
    Retorna as notas fiscais de entrada (SD1010) com paginação e filtros opcionais.
    """
    try:
        result = get_inbound_invoice_items(code, page, page_size, issue_date_start, issue_date_end, supplier, branch)
        return success_response(
            data=result,
            message=f"Inbound invoices for {code} fetched successfully (page {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar NF-es de entrada para {code}: {e}")
        return error_response(f"Unexpected error: {e}")

@router.get("/{code}/outbound-invoice-items", summary="Consulta as notas fiscais de saída (paginadas e filtráveis)")
def outbound_invoice_items(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    issue_date_start: Optional[str] = Query(None),
    issue_date_end: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    branch: Optional[str] = Query(None)
):
    """
    Retorna as notas fiscais de saída (SD2010) com paginação e filtros opcionais.
    """
    try:
        result = get_outbound_invoice_items(code, page, page_size, issue_date_start, issue_date_end, customer, branch)
        return success_response(
            data=result,
            message=f"Outbound invoices for {code} fetched successfully (page {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar NF-es de saída para {code}: {e}")
        return error_response(f"Unexpected error: {e}")
    
@router.get("/{code}/stock", summary="Consulta o estoque de um produto com filtros e paginação")
def stock(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    branch: Optional[str] = Query(None, description="Filial (B2_FILIAL)"),
    location: Optional[str] = Query(None, description="Local (B2_LOCAL)")
):
    """
    Retorna o estoque do produto consultando a tabela SB2010.
    Possui filtros opcionais para filial e local, além de paginação.
    """
    try:
        result = get_stock(code, page, page_size, branch, location)
        return success_response(
            data=result,
            message=f"Estoque de {code} retornado com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar estoque do item {code}: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get("/{code}/guide", summary="Consulta o roteiro de um produto e seus componentes com filtros e paginação")
def guide(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    branch: Optional[str] = Query(None, description="Filial (G2_FILIAL)"),
    max_depth: int = Query(10, ge=1, le=15)
):
    """
    Retorna o roteiro do produto consultando a tabela SG2010.
    Possui filtros opcionais para filial e local, além de paginação.
    """
    try:
        result = get_guide(code, page, page_size, branch, max_depth)
        return success_response(
            data=result,
            message=f"Roteiro de {code} retornado com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar roteiro do item {code}: {e}")
        return error_response(f"Erro inesperado: {e}")
    
@router.get(
    "/{code}/inspection",
    summary="Consulta a inspeção de processos do produto e seus componentes"
)
def inspection(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    max_depth: int = Query(10, ge=1, le=15)
):
    """
    Retorna a inspeção do produto consultando QP6, QP7 e QP8,
    incluindo inspeções dos componentes (via SG1010).
    """
    try:
        result = get_inspection(code, page, page_size, max_depth)
        return success_response(
            data=result,
            message=f"Inspeção de {code} retornada com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar inspeção do item {code}: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get(
    "/{code}/analyser",
    summary="Análise completa do produto (genérico + BOM + roteiro + inspeções)"
)
def product_analyser(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    max_depth: int = Query(10, ge=1, le=15)
):
    """
    Retorna:
    - Dados gerais do produto
    - Estrutura completa (produto + componentes)
    - Roteiro completo
    - Inspeções QP6/QP7/QP8 de produto e componentes
    """
    try:
        result = get_product_analyser(code, page, page_size, max_depth)
        return success_response(
            data=result,
            message=f"Análise completa de {code} retornada com sucesso."
        )
    except Exception as e:
        log_error(f"Erro ao analisar completamente o produto {code}: {e}")
        return error_response(f"Erro inesperado: {e}")


@router.get("/{code}/customers", summary="Consulta os clientes amarrados a um produto com paginação")
def customers(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    """
    Retorna os clientes vinculados a um produto (SA7010 — Amarração Produto x Cliente)
    com suporte a paginação.
    """
    try:
        result = get_customers(code, page, page_size)
        return success_response(
            data=result,
            message=f"Clientes vinculados ao produto {code} retornados com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar clientes do item {code}: {e}")
        return error_response(f"Erro inesperado: {e}")





