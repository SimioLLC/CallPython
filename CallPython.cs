using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Diagnostics;
using System.IO;

using SimioAPI;
using SimioAPI.Extensions;

namespace CallPython
{
    class CallPythonDefinition : IStepDefinition
    {
        #region IStepDefinition Members

        /// <summary>
        /// Property returning the full name for this type of step. The name should contain no spaces.
        /// </summary>
        public string Name
        {
            get { return "CallPython"; }
        }

        /// <summary>
        /// Property returning a short description of what the step does.
        /// </summary>
        public string Description
        {
            get { return "Description text for the 'CallPython' step."; }
        }

        /// <summary>
        /// Property returning an icon to display for the step in the UI.
        /// </summary>
        public System.Drawing.Image Icon
        {
            get { return null; }
        }

        /// <summary>
        /// Property returning a unique static GUID for the step.
        /// </summary>
        public Guid UniqueID
        {
            get { return MY_ID; }
        }
        static readonly Guid MY_ID = new Guid("{72e1c748-aa13-496c-b343-e05d6b70cd2e}");

        /// <summary>
        /// Property returning the number of exits out of the step. Can return either 1 or 2.
        /// </summary>
        public int NumberOfExits
        {
            get { return 1; }
        }

        /// <summary>
        /// Method called that defines the property schema for the step.
        /// </summary>
        public void DefineSchema(IPropertyDefinitions schema)
        {
            // Example of how to add a property definition to the step.
            IPropertyDefinition pd;
            pd = schema.AddStringProperty("PythonExecutableLocation", "python.exe");
            pd.DisplayName = "Python Executable Location";
            pd.Description = "Python Executable Location Desc";
            pd.Required = true;

            pd = schema.AddStringProperty("PythonScriptPath", String.Empty);
            pd.DisplayName = "Python Script Path";
            pd.Description = "Python Script Path Desc";
            pd.Required = true;
        }

        /// <summary>
        /// Method called to create a new instance of this step type to place in a process.
        /// Returns an instance of the class implementing the IStep interface.
        /// </summary>
        public IStep CreateStep(IPropertyReaders properties)
        {
            return new CallPython(properties);
        }

        #endregion
    }

    class CallPython : IStep
    {
        IPropertyReaders _properties;
        IPropertyReader _pythonScriptPathProp;
        IPropertyReader _pythonExecutableLocationProp;

        public CallPython(IPropertyReaders properties)
        {
            _properties = properties;
            _pythonScriptPathProp = _properties.GetProperty("PythonScriptPath");
            _pythonExecutableLocationProp = _properties.GetProperty("PythonExecutableLocation");
        }

        #region IStep Members

        /// <summary>
        /// Method called when a process token executes the step.
        /// </summary>
        public ExitType Execute(IStepExecutionContext context)
        {
           // full path to .py file
            string pyScriptPath = _pythonScriptPathProp.GetStringValue(context);
            string argsFile = string.Format("{0}", Path.GetDirectoryName(pyScriptPath));

            // python executable
            string pyExecutableLocation = _pythonExecutableLocationProp.GetStringValue(context);

            // create new process start info 
            ProcessStartInfo prcStartInfo = new ProcessStartInfo
            {
                // full path of the Python interpreter 'python.exe'
                FileName = pyExecutableLocation, // string.Format(@"""{0}""", "python.exe"),
                UseShellExecute = false,
                RedirectStandardOutput = false,
                CreateNoWindow = false // set to true if not debugging so the cmd doesn't flash up.
            };

            prcStartInfo.Arguments = string.Format("{0}", string.Format(@"""{0}""", pyScriptPath));

            using (Process process = Process.Start(prcStartInfo))
            {
                process.WaitForExit();
            }

            // Example of how to display a trace line for the step.
            context.ExecutionInformation.TraceInformation(String.Format("Executed Python"));

            return ExitType.FirstExit;
        }

        #endregion
    }
}
