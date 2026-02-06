from rest_framework.pagination import CursorPagination

class CustomCursorPagination(CursorPagination):
    page_size = 30
    page_size_query_param = "limit"
    max_page_size = 100
    ordering = ['-id']