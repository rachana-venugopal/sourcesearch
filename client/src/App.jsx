// App.jsx

// We begin by importing the necessary tools from the React library.
// 'useState' is a React Hook that lets us add a "state variable" to our component.
// Think of state as any data that changes over time in your application, like user input or fetched data.
// We also import the CSS file for styling our component.
import React, { useState } from 'react';
import './App.css';

// This is our main App component. In React, components are like JavaScript functions
// that return HTML (or more accurately, JSX). They are the building blocks of your UI.
function App() {
  // Here, we define our component's state variables using the 'useState' Hook.
  // A state variable is declared with a name (e.g., 'githubUrl') and a function to update it (e.g., 'setGithubUrl').
  
  // 'githubUrl' will store the text the user types into the input field.
  // It's initialized to an empty string ''.
  const [githubUrl, setGithubUrl] = useState('');

  // 'loading' is a boolean (true or false) that will help us show a loading message
  // while we are "fetching" the repository data. It's initialized to 'false'.
  const [loading, setLoading] = useState(false);

  // 'results' will store the repository data we get back from our "backend".
  // It's initialized to an empty array [] because we expect a list of repositories.
  const [results, setResults] = useState([]);
  
  // 'error' will hold any error messages we might want to display to the user.
  // It's initialized to 'null' because there are no errors at the start.
  const [error, setError] = useState(null);

  // This function is called when the user clicks the "Generate" button.
  // We use 'async' because we'll be simulating a network request, which is an asynchronous operation.
  const handleSubmit = async (event) => {
    // 'event.preventDefault()' stops the browser's default behavior of refreshing the page when a form is submitted.
    event.preventDefault();

    // --- Input Validation ---
    // It's good practice to check if the user has actually entered something.
    if (!githubUrl.trim()) {
      setError('Please enter a GitHub URL.');
      return; // Stop the function if the input is empty.
    }
    
    // --- Start the Loading Process ---
    // We set loading to 'true' to indicate that our app is now busy.
    setLoading(true);
    // We clear any previous results and errors to make way for new ones.
    setResults([]);
    setError(null);

    // --- Simulating a Backend Call ---
    // In a real application, you would make a network request (e.g., using 'fetch') to your backend here.
    // For this example, we'll just pretend by waiting for 2 seconds and then showing some fake data.
    // This 'try...catch' block helps us handle any potential errors during the "fetch".
    try {
      // 'setTimeout' is a JavaScript function that waits for a specified time before running code.
      await new Promise(resolve => setTimeout(resolve, 2000));

      // This is our mock (fake) data. A real API would return something like this.
      // Each object in the array represents a repository with its name and a 'cosine_similarity' score.
      const mockData = [
        { repo_name: 'expressjs/express', cosine_similarity: 0.98 },
        { repo_name: 'facebook/react', cosine_similarity: 0.92 },
        { repo_name: 'tensorflow/tensorflow', cosine_similarity: 0.85 },
        { repo_name: 'vuejs/vue', cosine_similarity: 0.78 },
        { repo_name: 'twbs/bootstrap', cosine_similarity: 0.65 },
      ];

      // We update our 'results' state with the data we "received".
      setResults(mockData);

    } catch (err) {
      // If something went wrong during the process, we'd catch the error here.
      setError('Failed to fetch repositories. Please try again.');
    } finally {
      // The 'finally' block always runs, whether the 'try' succeeded or the 'catch' was triggered.
      // We set 'loading' back to 'false' because the process is now complete.
      setLoading(false);
    }
  };

  // This is a helper function to turn a similarity score (0.0 to 1.0) into a star rating (1-5).
  const renderStars = (similarity) => {
    // We convert the score to a 0-5 scale and round it to the nearest whole number.
    // We use Math.max(1, ...) to ensure a repository gets at least one star.
    const starCount = Math.max(1, Math.round(similarity * 5));
    // 'Array.from({ length: starCount })' creates an array with 'starCount' empty slots.
    // We then map over it to create a '⭐' for each slot and join them together.
    return Array.from({ length: starCount }, (_, i) => '⭐').join('');
  };

  // The 'return' statement contains the JSX that describes what the component should render on the screen.
  // It looks like HTML, but it's actually JavaScript!
  return (
    <div className="container">
      <header className="header">
        <h1>RepoFinder</h1>
        <p>Enter a GitHub repository URL to discover similar projects.</p>
      </header>

      {/* 
        This is our form. We use the 'onSubmit' event to call our 'handleSubmit' function.
        This is generally better than using 'onClick' on the button, as it also handles submissions via the Enter key.
      */}
      <form onSubmit={handleSubmit} className="form">
        <input
          type="text"
          className="url-input"
          value={githubUrl} // The value of the input is tied to our 'githubUrl' state. This is called a "controlled component".
          onChange={(e) => setGithubUrl(e.target.value)} // When the user types, we update the 'githubUrl' state.
          placeholder="e.g., https://github.com/facebook/react"
        />
        <button type="submit" className="generate-button" disabled={loading}>
          {/* 
            This is a conditional render.
            If 'loading' is true, the button text will be "Generating...".
            Otherwise, it will be "Generate".
            The 'disabled={loading}' attribute also prevents the user from clicking the button while it's loading.
          */}
          {loading ? 'Generating...' : 'Generate'}
        </button>
      </form>

      {/* --- Conditional Rendering Section --- */}

      {/* If 'loading' is true, this 'div' will be displayed. The '&&' is a shortcut for a simple if-statement. */}
      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Analyzing repositories...</p>
        </div>
      )}

      {/* If there is an 'error' message, this 'div' will be displayed. */}
      {error && <div className="error-message">{error}</div>}

      {/* 
        If there are items in the 'results' array (results.length > 0), this section will be displayed.
        This prevents us from showing an empty list.
      */}
      {results.length > 0 && (
        <div className="results-container">
          <h2>Top 5 Similar Repositories</h2>
          <ul className="results-list">
            {/* 
              We use the '.map()' method to loop over our 'results' array.
              For each 'repo' object in the array, we create a list item '<li>'.
              The 'key' attribute is important for React to keep track of each item in the list efficiently.
            */}
            {results.map((repo) => (
              <li key={repo.repo_name} className="result-item">
                <span className="repo-name">{repo.repo_name}</span>
                <span className="stars">{renderStars(repo.cosine_similarity)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// We export the App component so it can be used in other files, like 'main.jsx'.
export default App;