"""
把 data/ 下的结果文件提交回仓库（使用 GITHUB_TOKEN）
"""
import sys
import subprocess


def run(cmd):
    print('>', ' '.join(cmd))
    subprocess.check_call(cmd)


def main():
    files = sys.argv[1:]
    if not files:
        print('no files to commit')
        return

    run(['git', 'config', '--local', 'user.email', 'action@github.com'])
    run(['git', 'config', '--local', 'user.name', 'github-actions'])
    run(['git', 'add'] + files)

    try:
        run(['git', 'commit', '-m', 'Auto: update scraped funds and signals [skip ci]'])
    except subprocess.CalledProcessError:
        print('nothing to commit')
        return

    # push using token (GITHUB_TOKEN is already available to Actions and has write access)
    run(['git', 'push', 'origin', 'HEAD:refs/heads/' + subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()])


if __name__ == '__main__':
    main()
