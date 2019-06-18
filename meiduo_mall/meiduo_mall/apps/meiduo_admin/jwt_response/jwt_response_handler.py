


def custom_jwt_response_handler(token, user=None, request=None):

    return {
        "username": user.username,
        "user_id": user.id,
        "token": token
    }