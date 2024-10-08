from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model, authenticate
from .serializers import UserSerializer, LoginSerializer
from utils.pagination import (
    CustomPageNumberPagination,
    CustomLimitOffsetPagination,
    CustomCursorPagination,
)
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from utils.response import CustomResponse

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    用户视图集，支持用户的CRUD操作
    """

    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    pagination_class = CustomPageNumberPagination

    def get_permissions(self):
        """
        根据不同的操作来设置权限
        """
        if self.action in ["create"]:
            # 注册新用户时允许任何人访问
            permission_classes = [AllowAny]
        else:
            # 对于其他操作，要求用户认证
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def destroy(self, request, *args, **kwargs):
        # 重写禁用删除功能, 用户注销逻辑另写
        return Response(
            {"detail": "Delete operation is not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    # 自定义新方法，当使用DefaultRouter配置路由时，会自动使用函数名创建路径为 /get_self/
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def self(self, request):
        """
        根据 token 获取请求用户数据
        """
        user = request.user  # 从请求中获取当前用户
        serializer = self.get_serializer(user)
        return Response(serializer.data)


class LoginView(APIView):
    """
    登录类，调用auth的认证登录与JWT逻辑
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # 该接口不需要鉴权

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]
            user = authenticate(email=email, password=password)
            if user is not None:
                current_time = timezone.now()
                # 生成token
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token
                # 获取当前时间和过期时间+8小时
                expiration_time = current_time + access_token.lifetime + timezone.timedelta(hours=8)
                expiration_time_str = expiration_time.strftime("%Y/%m/%d %H:%M:%S")
                # 序列化user数据
                userdata = UserSerializer(user).data
                data = {"avatar": userdata["avatar"], "username": userdata["username"], "nickname": userdata["nickname"], "roles": ["admin"], "permissions": ["*:*:*"], "refreshToken": str(refresh), "accessToken": str(refresh.access_token), "expires": expiration_time_str}
                return CustomResponse(data=data, msg="登陆成功")

            return CustomResponse(success=False, msg="登录信息错误", status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AsyncRoutesView(APIView):
    """动态路由视图"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 模拟动态生成的路由数据
        permission_router = {
            "path": "/permission",
            "meta": {"title": "权限管理", "icon": "ep:lollipop", "rank": 2},
            "children": [
                {"path": "/permission/page/index", "name": "PermissionPage", "meta": {"title": "页面权限", "roles": ["admin", "common"]}},
                {
                    "path": "/permission/button",
                    "meta": {"title": "按钮权限", "roles": ["admin", "common"]},
                    "children": [
                        {"path": "/permission/button/router", "component": "permission/button/index", "name": "PermissionButtonRouter", "meta": {"title": "路由返回按钮权限", "auths": ["permission:btn:add", "permission:btn:edit", "permission:btn:delete"]}},
                        {"path": "/permission/button/login", "component": "permission/button/perms", "name": "PermissionButtonLogin", "meta": {"title": "登录接口返回按钮权限"}},
                    ],
                },
            ],
        }

        # 返回 JSON 响应
        return Response({"success": True, "data": [permission_router]}, status=status.HTTP_200_OK)
