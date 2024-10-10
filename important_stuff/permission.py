import discord

def moderator_permissions(user: discord.Member):
    mod_perms = [
        'kick_members', 'manage_messages', 'manage_nicknames', 'deafen_members', 'mute_members', 'moderate_members'
    ]
    user_perms = user.guild_permissions
    return all(getattr(user_perms, perm, False) for perm in mod_perms)

def admin_permissions(user: discord.Member):
    admin_perms = [
        'kick_members', 'ban_members', 'manage_channels', 'manage_guild', 'manage_messages',
        'manage_roles', 'administrator', 'manage_nicknames', 'deafen_members', 'mute_members',
        'moderate_members'
    ]
    user_perms = user.guild_permissions
    return all(getattr(user_perms, perm, False) for perm in admin_perms)