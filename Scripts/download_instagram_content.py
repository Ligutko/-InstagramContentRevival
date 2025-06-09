import sys
import instaloader
import os
import logging # Додаємо для кращого логування

# Налаштовуємо логування, щоб Instaloader не "засмічував" stdout
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
instaloader.log_target = sys.stderr # Направляємо логи Instaloader в stderr, щоб stdout був чистим для ZennoPoster
instaloader.compress_json = False # Не стискати JSON-файли метаданих

def download_instagram_content(
    username_to_scrape,
    output_folder,
    download_posts,
    download_reels,
    download_stories,
    proxy_address=None, # Приймаємо один проксі
    login_username=None, # Аргумент для логіну
    login_password=None  # Аргумент для паролю
):
    try:
        # Налаштування Instaloader
        loader = instaloader.Instaloader(
            dirname_pattern=os.path.join(output_folder, "{profile}"), # Шлях збереження
            filename_pattern="{date_utc}__{shortcode}" # Шаблон назви файлу
        )

        # Налаштування проксі (якщо передано)
        if proxy_address:
            # Очікуємо формат "ip:port:user:pass" або "ip:port"
            parts = proxy_address.split(':')
            if len(parts) == 4:
                # HTTP-проксі з аутентифікацією
                proxy_url = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
            elif len(parts) == 2:
                # HTTP-проксі без аутентифікації
                proxy_url = f"http://{parts[0]}:{parts[1]}"
            else:
                return f"ERROR: Invalid proxy format. Expected ip:port:user:pass or ip:port. Got: {proxy_address}"
            
            loader.context.proxies = {"http": proxy_url, "https": proxy_url}
            print(f"INFO: Using proxy: {proxy_url.split('@')[-1]}") # Логуємо проксі без логіна/пароля

        # --- Логін до Instagram ---
        if login_username and login_password:
            try:
                loader.load_session_from_file(login_username, os.path.join(output_folder, "instaloader_session"))
                print(f"INFO: Loaded session for {login_username}.")
            except FileNotFoundError:
                print(f"INFO: Session file not found for {login_username}. Logging in...")
                try:
                    loader.login(login_username, login_password)
                    loader.save_session_to_file(os.path.join(output_folder, "instaloader_session"))
                    print(f"INFO: Successfully logged in and saved session for {login_username}.")
                except instaloader.exceptions.BadCredentialsException:
                    return f"ERROR: Bad Instagram credentials for {login_username}."
                except instaloader.exceptions.TwoFactorAuthRequiredException:
                    return f"ERROR: Two-factor authentication required for {login_username}. Manual login needed."
                except Exception as e:
                    return f"ERROR: Failed to log in {login_username}: {str(e)}"
        else:
            print("WARNING: Not logged in. Downloads may be severely limited or blocked.")


        # --- Отримання Профілю (один раз) ---
        try:
            profile = instaloader.Profile.from_username(loader.context, username_to_scrape)
            print(f"INFO: Profile '{username_to_scrape}' found.")
        except instaloader.exceptions.ProfileNotExistsException:
            return f"ERROR: Profile '{username_to_scrape}' does not exist or is private."
        except Exception as e:
            return f"ERROR: Failed to get profile '{username_to_scrape}': {str(e)}"

        # --- Завантаження Контенту ---
        downloaded_count = 0

        # Пости (включають фото, відео, рілси)
        if download_posts:
            print(f"INFO: Downloading posts from '{username_to_scrape}'...")
            try:
                for post in loader.get_json(f"https://www.instagram.com/{profile.username}/?__a=1&__d=1"): # Modern way to get posts from profile (requires login)
                    loader.download_post(post, target=os.path.join(output_folder, profile.username))
                    downloaded_count += 1
                print(f"INFO: Finished downloading posts for '{username_to_scrape}'.")
            except Exception as e:
                print(f"WARNING: Failed to download posts for '{username_to_scrape}': {str(e)}")

        # Різи (може бути дублюванням з постами, але явно для рілсів)
        if download_reels:
            print(f"INFO: Downloading reels from '{username_to_scrape}'...")
            try:
                # get_json for reels from profile, this needs proper filtering
                for post in profile.get_posts(): # Iterate through all posts
                    if post.is_reel: # Check if it's a reel
                        loader.download_post(post, target=os.path.join(output_folder, profile.username))
                        downloaded_count += 1
                print(f"INFO: Finished downloading reels for '{username_to_scrape}'.")
            except Exception as e:
                print(f"WARNING: Failed to download reels for '{username_to_scrape}': {str(e)}")

        # Історії
        if download_stories:
            print(f"INFO: Downloading stories from '{username_to_scrape}'...")
            try:
                # This fetches story items directly
                for story in loader.get_stories(profile.userid):
                    loader.download_story(story, target=os.path.join(output_folder, profile.username))
                    downloaded_count += 1
                print(f"INFO: Finished downloading stories for '{username_to_scrape}'.")
            except Exception as e:
                print(f"WARNING: Failed to download stories for '{username_to_scrape}': {str(e)}")

        return f"SUCCESS: Downloaded {downloaded_count} items to {os.path.join(output_folder, profile.username)}"

    except Exception as overall_e:
        return f"ERROR: An unhandled error occurred: {str(overall_e)}"


if __name__ == "__main__":
    # Очікувані аргументи:
    # --username <username_to_scrape>
    # --output <output_folder_path>
    # --posts True/False
    # --reels True/False
    # --stories True/False
    # --proxy <proxy_address> (optional, e.g., 107.167.27.58:28008:8BujgUgU:YX2h7Fas)
    # --login_user <instagram_login_username> (optional)
    # --login_pass <instagram_login_password> (optional)

    args = sys.argv[1:]
    
    # Парсинг аргументів
    username_to_scrape = args[args.index('--username') + 1]
    output_folder = args[args.index('--output') + 1]
    download_posts = args[args.index('--posts') + 1].lower() == "true"
    download_reels = args[args.index('--reels') + 1].lower() == "true"
    download_stories = args[args.index('--stories') + 1].lower() == "true"
    
    proxy_address = args[args.index('--proxy') + 1] if '--proxy' in args else None
    login_username = args[args.index('--login_user') + 1] if '--login_user' in args else None
    login_password = args[args.index('--login_pass') + 1] if '--login_pass' in args else None

    # Виклик основної функції
    result = download_instagram_content(
        username_to_scrape,
        output_folder,
        download_posts,
        download_reels,
        download_stories,
        proxy_address,
        login_username,
        login_password
    )
    print(result)