import subprocess
import json
import sys
import os
import ctypes # 用于检查管理员权限

# 配置文件路径
CONFIG_FILE = 'network_configs.json'

def is_admin():
    """检查是否以管理员身份运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def load_configs(filepath):
    """从文件加载配置"""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"加载配置文件失败: {e}")
        return {}

def save_configs(configs, filepath):
    """将配置保存到文件"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=4, ensure_ascii=False) # ensure_ascii=False 避免中文乱码
        print("配置已保存。")
    except IOError as e:
        print(f"保存配置文件失败: {e}")

def list_adapters():
    """列出所有网络适配器名称"""
    print("正在获取网络适配器列表...")
    try:
        # 使用 PowerShell 获取更友好的适配器名称
        # 或者使用 netsh interface show interface 获取 Interface Name
        result = subprocess.run(['netsh', 'interface', 'show', 'interface'], capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            print("获取适配器列表失败:", result.stderr)
            return []

        adapters = []
        lines = result.stdout.strip().split('\n')
        # 跳过前几行（标题行）
        for line in lines[3:]:
            parts = line.split(None, 3) # 最多分割3次，获取Interface Name部分
            if len(parts) > 3:
                adapter_name = parts[3].strip()
                if adapter_name: # 确保名称非空
                     adapters.append(adapter_name)
        return adapters
    except FileNotFoundError:
        print("未找到netsh命令，请确认系统环境。")
        return []
    except Exception as e:
        print(f"获取适配器列表过程中发生错误: {e}")
        return []


def set_static_ip(adapter_name, ip_address, subnet_mask, gateway, dns_servers=None):
    """设置静态IP、子网掩码、网关和DNS"""
    print(f"\n正在为适配器 '{adapter_name}' 设置静态IP...")
    try:
        # 设置静态IP、子网掩码和网关
        cmd_ip = ['netsh', 'interface', 'ipv4', 'set', 'address',
                  f'name="{adapter_name}"', 'static', ip_address, subnet_mask, gateway, '1'] # 最后一个参数是网关跃点，通常为1
        result_ip = subprocess.run(cmd_ip, capture_output=True, text=True, encoding='utf-8', check=True)
        print("IP地址、子网掩码、网关设置成功。")

        # 设置DNS
        if dns_servers:
            # 先设置为DHCP获取，清空之前的静态设置
            cmd_dns_dhcp = ['netsh', 'interface', 'ipv4', 'set', 'dnsserver',
                            f'name="{adapter_name}"', 'source=dhcp']
            subprocess.run(cmd_dns_dhcp, capture_output=True, text=True, encoding='utf-8') # 不检查错误，因为可能本来就是静态的

            # 设置主DNS
            cmd_dns_primary = ['netsh', 'interface', 'ipv4', 'set', 'dnsserver',
                               f'name="{adapter_name}"', 'static', dns_servers[0], 'primary']
            subprocess.run(cmd_dns_primary, capture_output=True, text=True, encoding='utf-8', check=True)
            print(f"主DNS服务器 {dns_servers[0]} 设置成功。")

            # 设置备用DNS
            for i, dns in enumerate(dns_servers[1:]):
                cmd_dns_secondary = ['netsh', 'interface', 'ipv4', 'add', 'dnsserver',
                                     f'name="{adapter_name}"', dns, f'index={i+2}'] # 备用DNS索引从2开始
                subprocess.run(cmd_dns_secondary, capture_output=True, text=True, encoding='utf-8', check=True)
                print(f"备用DNS服务器 {dns} 设置成功。")
        else:
             # 如果没有提供DNS，就设置为DHCP获取DNS
            cmd_dns_dhcp = ['netsh', 'interface', 'ipv4', 'set', 'dnsserver',
                            f'name="{adapter_name}"', 'source=dhcp']
            subprocess.run(cmd_dns_dhcp, capture_output=True, text=True, encoding='utf-8')
            print("DNS设置为自动获取 (DHCP)。")

        print("静态IP配置应用完成。")
    except subprocess.CalledProcessError as e:
        print(f"设置网络配置失败: {e.stderr}")
    except Exception as e:
        print(f"设置网络配置过程中发生错误: {e}")


def set_dhcp(adapter_name):
    """设置适配器为DHCP自动获取IP和DNS"""
    print(f"\n正在将适配器 '{adapter_name}' 设置为DHCP...")
    try:
        # 设置IP为DHCP
        cmd_ip_dhcp = ['netsh', 'interface', 'ipv4', 'set', 'address',
                       f'name="{adapter_name}"', 'source=dhcp']
        result_ip = subprocess.run(cmd_ip_dhcp, capture_output=True, text=True, encoding='utf-8', check=True)
        print("IP地址设置为自动获取 (DHCP)。")

        # 设置DNS为DHCP
        cmd_dns_dhcp = ['netsh', 'interface', 'ipv4', 'set', 'dnsserver',
                        f'name="{adapter_name}"', 'source=dhcp']
        result_dns = subprocess.run(cmd_dns_dhcp, capture_output=True, text=True, encoding='utf-8', check=True)
        print("DNS设置为自动获取 (DHCP)。")

        print("DHCP配置应用完成。")
    except subprocess.CalledProcessError as e:
        print(f"设置DHCP失败: {e.stderr}")
    except Exception as e:
        print(f"设置DHCP过程中发生错误: {e}")

def get_adapter_choice(adapter_list):
    """让用户选择网络适配器"""
    if not adapter_list:
        print("未找到可用的网络适配器。")
        return None

    print("\n请选择要操作的网络适配器:")
    for i, adapter in enumerate(adapter_list):
        print(f"{i + 1}. {adapter}")

    while True:
        try:
            choice = int(input(f"请输入数字 (1-{len(adapter_list)}): "))
            if 1 <= choice <= len(adapter_list):
                return adapter_list[choice - 1]
            else:
                print("输入无效，请重新输入。")
        except ValueError:
            print("输入无效，请输入数字。")

def create_new_config():
    """创建新的配置模板"""
    print("\n--- 创建新配置模板 ---")
    adapters = list_adapters()
    if not adapters:
        return None

    selected_adapter = get_adapter_choice(adapters)
    if not selected_adapter:
        return None

    template_name = input("请输入模板名称: ").strip()
    if not template_name:
        print("模板名称不能为空。")
        return None

    ip_address = input("请输入本机IPv4地址: ").strip()
    # 可以添加简单的IP格式校验
    if not ip_address:
        print("IP地址不能为空。")
        return None

    subnet_mask = input("请输入子网掩码 (默认 255.255.255.0): ").strip() or "255.255.255.0"

    gateway = input("请输入默认网关 (如果不需要请留空): ").strip()

    dns_input = input("请输入DNS服务器地址 (多个用逗号分隔，如果不需要请留空): ").strip()
    dns_servers = [dns.strip() for dns in dns_input.split(',') if dns.strip()] if dns_input else None

    new_config = {
        'adapter': selected_adapter,
        'ip': ip_address,
        'subnet': subnet_mask,
        'gateway': gateway,
        'dns': dns_servers
    }
    return {template_name: new_config}

def main():
    """主函数"""
    if not is_admin():
        print("请以管理员身份运行此脚本。")
        # 如果不是管理员，尝试重新启动脚本为管理员模式 (复杂，这里简单提示)
        # import elevate # 可以使用 elevate 库，但需要额外安装
        # elevate.elevate()
        # 如果 elevate 成功，代码会在这里重新运行
        # 如果不使用 elevate，直接退出
        sys.exit(1)


    configs = load_configs(CONFIG_FILE)

    while True:
        print("\n--- IPv4 配置切换工具 ---")
        print("1. 列出可用网络适配器")
        print("2. 列出已有配置模板")
        print("3. 创建新配置模板")
        print("4. 应用配置模板")
        print("5. 切换到DHCP模式")
        print("6. 保存配置模板 (如果修改过)")
        print("7. 退出")

        choice = input("请输入操作编号: ").strip()

        if choice == '1':
            adapters = list_adapters()
            if adapters:
                print("\n可用网络适配器:")
                for adapter in adapters:
                    print(f"- {adapter}")
        elif choice == '2':
            if not configs:
                print("\n当前没有保存的配置模板。")
            else:
                print("\n已有配置模板:")
                for name, config in configs.items():
                    print(f"- {name}:")
                    print(f"  适配器: {config.get('adapter', '未知')}")
                    print(f"  IP: {config.get('ip', '未知')}")
                    print(f"  子网掩码: {config.get('subnet', '未知')}")
                    print(f"  网关: {config.get('gateway', '无')}")
                    dns_servers = config.get('dns')
                    if dns_servers:
                        print(f"  DNS: {', '.join(dns_servers)}")
                    else:
                        print("  DNS: 自动获取或无")
        elif choice == '3':
            new_config_entry = create_new_config()
            if new_config_entry:
                configs.update(new_config_entry)
                print("\n新配置模板已添加。")
                # 创建后自动保存
                save_configs(configs, CONFIG_FILE)

        elif choice == '4':
            if not configs:
                print("\n没有可用的配置模板，请先创建。")
                continue

            print("\n请选择要应用的配置模板:")
            template_names = list(configs.keys())
            for i, name in enumerate(template_names):
                print(f"{i + 1}. {name}")

            while True:
                try:
                    template_choice = int(input(f"请输入模板编号 (1-{len(template_names)}): "))
                    if 1 <= template_choice <= len(template_names):
                        selected_template_name = template_names[template_choice - 1]
                        selected_config = configs[selected_template_name]
                        # 再次获取适配器列表，确保选中的适配器仍然存在
                        adapters = list_adapters()
                        if selected_config['adapter'] not in adapters:
                             print(f"警告: 模板中的适配器 '{selected_config['adapter']}' 未找到。请检查网络连接。")
                             # 尝试让用户从当前可用适配器中选择
                             print("\n请从当前可用适配器中选择一个应用此模板:")
                             selected_adapter_for_apply = get_adapter_choice(adapters)
                             if selected_adapter_for_apply:
                                 selected_config['adapter'] = selected_adapter_for_apply
                                 print(f"已选择适配器 '{selected_adapter_for_apply}' 应用模板。")
                             else:
                                 print("无法应用模板，请稍后再试。")
                                 break # 跳出模板选择循环
                        # 如果适配器存在或已重新选择
                        if 'adapter' in selected_config and selected_config['adapter'] in list_adapters(): # 再次确认适配器存在
                            set_static_ip(selected_config['adapter'],
                                          selected_config['ip'],
                                          selected_config['subnet'],
                                          selected_config['gateway'],
                                          selected_config.get('dns'))
                        break # 跳出模板选择循环
                    else:
                        print("输入无效，请重新输入。")
                except ValueError:
                    print("输入无效，请输入数字。")
        elif choice == '5':
            adapters = list_adapters()
            if not adapters:
                continue
            selected_adapter = get_adapter_choice(adapters)
            if selected_adapter:
                set_dhcp(selected_adapter)
        elif choice == '6':
            save_configs(configs, CONFIG_FILE)
        elif choice == '7':
            print("退出脚本。")
            break
        else:
            print("无效的输入，请重新输入。")

if __name__ == "__main__":
    main()
