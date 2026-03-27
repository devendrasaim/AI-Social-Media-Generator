# AI Automated Social Media Generator Workflow

This document visualizes the complete automation workflow of the project, from topic brainstorming to Instagram publishing.

## Automation Flowchart

```mermaid
graph TD
    %% Starting Point
    Start((Run automate.py)) --> Lock[Acquire Process Lock]
    Lock --> NotifyStart[Notify: Starting Automation]

    %% Queue Management
    NotifyStart --> CheckQueue{Queue Low? < 3}
    CheckQueue -- Yes --> Brainstorm[Brainstorm New Topics<br/>core.brainstormer]
    CheckQueue -- No --> Maintenance[Run Maintenance<br/>Clear old files/temp]
    Brainstorm --> Maintenance

    %% Topic Selection
    Maintenance --> GetTopic[Pick Topic from<br/>topics_queue.txt]
    GetTopic --> NextStep{Topic Found?}
    NextStep -- No --> EndNoTopic((End: No Topics))
    
    %% Pipeline Execution (main.py)
    NextStep -- Yes --> RunMain[Invoke main.py --publish]
    
    subgraph Repurposing Pipeline
        RunMain --> Source{Content Source}
        Source -- YouTube --> YT[Extract Video Content<br/>core.content_engine]
        Source -- Perplexity --> PPLX[Fetch Latest Info<br/>core.content_engine]
        
        YT --> Process[Generate Slides & Captions<br/>Gemini 1.5 Pro]
        PPLX --> Process
        
        Process --> Visuals[Generate Image URLs<br/>Google Imagen 4.0]
        Visuals --> Download[Download Images to<br/>carousel_review/]
    end

    %% Publishing & Logging
    Download --> Publish[Publish to Instagram<br/>Blotato.ai]
    Publish --> Log[Log to CSV<br/>published_posts.csv]
    
    Log --> SuccessNotify[Notify: Success/Failure]
    SuccessNotify --> Unlock[Release Process Lock]
    Unlock --> End((End: Run Complete))

    %% Error Handling
    Process -.->|Failure| ErrNotify[Notify: Failure]
    Visuals -.->|Failure| ErrNotify
    Publish -.->|Failure| ErrNotify
    ErrNotify --> Unlock
```

## Key Components

### 1. Automation Trigger (`automate.py`)
- **Queue Management**: Automatically refills the `topics_queue.txt` when it drops below 3 topics using Gemini-powered brainstorming.
- **Maintenance**: Deletes old review images and clears the `/temp` directory to save disk space.
- **Locking**: Prevents multiple instances from running concurrently.

### 2. Content Pipeline (`main.py`)
- **Sourcing**: Can ingest content from a YouTube URL or search the web via Perplexity for the latest AI/Tech news.
- **Content Engine**: Uses Gemini to transform complex information into engaging carousel slides, captions, and niche-specific hashtags.
- **Visual Engine**: Uses Google Imagen 4.0 to generate premium, brand-consistent visuals for each slide.

### 3. Distribution & Tracking
- **Blotato Integration**: Handles the API connection to Instagram for seamless publishing.
- **Multi-Channel Notifications**: Sends real-time status updates via Discord and Email.
- **Logging**: Maintains a `published_posts.csv` file for historical tracking and analytics.
