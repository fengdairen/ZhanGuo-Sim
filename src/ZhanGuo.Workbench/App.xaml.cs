using System.IO;
using System.Windows;
using System.Windows.Threading;

namespace ZhanGuo.Workbench;

public partial class App : Application
{
    private static readonly string LogPath =
        Path.Combine(AppContext.BaseDirectory, "workbench-error.log");

    protected override void OnStartup(StartupEventArgs e)
    {
        // 把任何未处理异常写进日志，避免“双击没反应”而无从排查
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
            Log("AppDomain", args.ExceptionObject as Exception);
        DispatcherUnhandledException += (_, args) =>
        {
            Log("Dispatcher", args.Exception);
            args.Handled = true;
            MessageBox.Show(args.Exception.Message, "工作台出错", MessageBoxButton.OK, MessageBoxImage.Error);
        };
        base.OnStartup(e);
    }

    private static void Log(string source, Exception? ex)
    {
        try
        {
            File.AppendAllText(LogPath,
                $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {source}\n{ex}\n\n");
        }
        catch { /* 日志失败不影响主流程 */ }
    }
}
