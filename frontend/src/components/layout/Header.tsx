import { Bell, Search as SearchIcon } from "lucide-react";

export function Header() {
  return (
    <header className="h-16 flex items-center justify-between px-6 bg-surface border-b border-border">
      <div className="flex items-center flex-1">
        <div className="relative w-96">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <SearchIcon className="h-4 w-4 text-secondary-foreground" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2 border border-input rounded-md leading-5 bg-background placeholder-secondary-foreground focus:outline-none focus:bg-surface focus:border-primary focus:ring-1 focus:ring-primary sm:text-sm transition-colors"
            placeholder="Search cases, customers, entities..."
          />
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success/10 border border-success/20">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
          <span className="text-xs font-medium text-success">AI Active</span>
        </div>
        
        <button className="p-2 text-secondary-foreground hover:text-foreground transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 block w-2 h-2 rounded-full bg-danger"></span>
        </button>

        <div className="flex items-center gap-3 pl-4 border-l border-border">
          <div className="flex flex-col items-end">
            <span className="text-sm font-medium text-foreground">Alex Mercer</span>
            <span className="text-xs text-secondary-foreground">L2 Analyst</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-primary-light flex items-center justify-center text-primary font-medium border border-primary/20">
            AM
          </div>
        </div>
      </div>
    </header>
  );
}
